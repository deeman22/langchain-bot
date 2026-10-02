import os
import sqlite3

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_bot.rag_tool import search_policies
from langgraph.checkpoint.sqlite import SqliteSaver
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
        search_policies
    ]

    system_prompt = """
You are an e-commerce support assistant.

You can have normal conversations with users.

For greetings, introductions, memory questions,
and casual conversation, answer directly.

Use the search_policies tool ONLY when the user
asks about:

- returns
- refunds
- shipping
- cancellation policies

If information is already available in the
conversation history, use it.
"""

    return create_agent(
        model=llm,
        tools=tools,
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
]