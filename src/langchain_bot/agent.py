import os
import sqlite3

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_bot.rag_tool import search_policies
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_bot.middleware import get_logging_middleware
from langchain_bot.sql_tools import get_sql_tools
from langchain_bot.gmail_tools import get_gmail_tools
from langchain_bot.action_tools import get_action_tools
from langchain_bot.context import SessionContext
from langchain.tools import ToolRuntime, tool

load_dotenv()

_agent = None
_checkpointer = None

# @tool(description="Return the current authenticated user")
# def who_am_i(runtime: ToolRuntime[SessionContext]) -> str:
#     return (
#         f"email={runtime.context.user_email}, "
#         f"role={runtime.context.role}"
#     )

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

    _checkpointer = SqliteSaver(conn=conn)
    _checkpointer.setup()

    return _checkpointer


def create_support_agent():
    """
    Create an e-commerce customer support agent.
    """

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2
    )

    tools = [
        search_policies,
        *get_sql_tools(),
        *get_gmail_tools(),
        *get_action_tools()
    ]

    system_prompt = system_prompt = system_prompt = """
You are an e-commerce support assistant.

You can have normal conversations with users.

For greetings, introductions, memory questions,
and casual conversation, answer directly.

Capability 1: Policy Knowledge

Use search_policies for questions about:

- returns
- refunds
- shipping
- cancellations
- company policies
- FAQs

Always use the tool when policy information is needed.


Capability 2: Customer Order Data

Use SQL database tools for questions about:

- my orders
- order status
- order details
- my returns
- my payments
- customer purchases

Always inspect the database schema when needed
before querying.

Use tool results to answer customer-specific questions.


Capability 3: Email Notifications

When a customer requests confirmation emails,
return requests, cancellation requests,
refund confirmations, or support acknowledgements,
use the Gmail tool when available.

Only send emails when the user explicitly asks
for an email or when a confirmation email is required.


General Rules

- Use tool results as the source of truth.
- Do not invent order information.
- Do not invent policy information.
- If information is unavailable, say so.
- Be concise and helpful.
"""

    return create_agent(
        model=llm,
        tools=tools,
        context_schema=SessionContext,
        system_prompt=system_prompt,
        middleware=get_logging_middleware(),
        checkpointer=get_checkpointer()
    )


def get_agent():
    """
    Singleton agent instance.
    """

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
    "get_thread_config",
    "reset_agent"
]