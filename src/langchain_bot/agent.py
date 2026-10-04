import os
import sqlite3

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    dynamic_prompt,
    ModelRequest,
)

from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_bot.context import SessionContext
from langchain_bot.rag_tool import search_policies
from langchain_bot.sql_tools import get_sql_tools
from langchain_bot.gmail_tools import get_gmail_tools
from langchain_bot.action_tools import get_action_tools
from langchain_bot.middleware import get_logging_middleware


load_dotenv()


_agent = None
_checkpointer = None


def get_checkpointer():

    global _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    db_path = os.getenv(
        "CHECKPOINTS_DB_PATH",
        "checkpoints.sqlite"
    )

    conn = sqlite3.connect(
        db_path,
        check_same_thread=False
    )

    _checkpointer = SqliteSaver(
        conn=conn
    )

    _checkpointer.setup()

    return _checkpointer


BASE_SYSTEM_PROMPT = """
You are an e-commerce customer support assistant.

You can have normal conversations with users.

You have four capabilities.


CAPABILITY 1 — POLICIES

Use search_policies for:

- returns policy
- refund policy
- shipping policy
- cancellation policy
- FAQs

Never invent policy information.


CAPABILITY 2 — CUSTOMER DATABASE

Use SQL tools for read-only customer-specific questions:

- my orders
- order status
- order details
- order items
- returns
- payments
- spending
- tickets

IMPORTANT:

The authenticated user's email is supplied below.

Every customer-specific SQL query MUST verify ownership
using that email.

Never expose another user's data.

SQL toolkit tools are READ ONLY for this workflow.
Never use SQL tools to UPDATE, INSERT or DELETE data.

All database mutations must happen only through the
approved action tools.

Make at most 3 SQL query attempts for one user request.
If the required information cannot be established after
3 attempts, explain that you could not verify it.


CAPABILITY 3 — EMAIL

If Gmail is available, you may send a "request received"
confirmation email when appropriate.

Use the authenticated customer's email.

Do not invent an email address.

Never send an email to another customer's address.


CAPABILITY 4 — CANCEL / RETURN ACTIONS

Cancellation flow:

1. Use SQL tools to verify:
   - the order belongs to the authenticated user
   - the order status is PLACED

2. If verification fails, explain why and STOP.

3. If Gmail is available and a request-received email is
   appropriate, send it.

4. Then call:
   cancel_order_action(order_id)

The action tool requires admin approval.
Do not claim the order was cancelled before approval.


Return flow:

1. Use SQL tools to verify:
   - the order belongs to the authenticated user
   - status is SHIPPED or DELIVERED
   - the exact product exists in that order

2. If status is PLACED:
   tell the customer to cancel instead.
   Do NOT call create_return_action.

3. Ask for a return reason if it is missing.

4. If Gmail is available and appropriate, send a
   request-received email.

5. Then call:
   create_return_action(
       order_id,
       product_name,
       reason
   )

The action tool requires admin approval.

Do not claim a return or cancellation has completed
until the action tool actually executes after approval.


TOOL RULES

Never request more than ONE tool in a single model response.

After receiving a tool result, reason again before calling
another tool.

Never call both action tools for the same request.

Never retry an action tool while approval is pending.

If an admin rejects an action, tell the customer it was
not approved and do not retry unless the customer makes
a new explicit request.
"""


@dynamic_prompt
def support_prompt(
    request: ModelRequest
) -> str:

    context = request.runtime.context

    if context is None:
        return BASE_SYSTEM_PROMPT

    return (
        BASE_SYSTEM_PROMPT
        + "\n\n"
        + "AUTHENTICATED SESSION\n"
        + f"Email: {context.user_email}\n"
        + f"Role: {context.role}\n"
        + f"Conversation ID: {context.conversation_id}\n"
    )


def create_support_agent():

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2
    )

    tools = [
        search_policies,
        *get_sql_tools(),
        *get_gmail_tools(),
        *get_action_tools(),
    ]

    hitl_middleware = HumanInTheLoopMiddleware(
        interrupt_on={
            "cancel_order_action": {
                "allowed_decisions": [
                    "approve",
                    "reject"
                ],
                "description": (
                    "Approve or reject this "
                    "order cancellation."
                )
            },
            "create_return_action": {
                "allowed_decisions": [
                    "approve",
                    "reject"
                ],
                "description": (
                    "Approve or reject this "
                    "product return."
                )
            }
        }
    )

    return create_agent(
        model=llm,
        tools=tools,
        middleware=[
            support_prompt,
            *get_logging_middleware(),
            hitl_middleware,
        ],
        checkpointer=get_checkpointer(),
        context_schema=SessionContext,
    )


def get_agent():

    global _agent

    if _agent is None:
        _agent = create_support_agent()

    return _agent


def reset_agent():

    global _agent
    _agent = None


def get_thread_config(
    user_email: str,
    conversation_id: str
):

    return {
        "configurable": {
            "thread_id":
                f"{user_email}:{conversation_id}"
        },
        "recursion_limit": 20
    }


__all__ = [
    "create_support_agent",
    "get_agent",
    "reset_agent",
    "get_thread_config",
]