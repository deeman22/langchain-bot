from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

load_dotenv()


def get_database():
    """
    Return the ecommerce SQLite database.
    """

    db_path = (
        Path(__file__).resolve()
        .parent.parent.parent
        / "ecommerce.db"
    )

    return SQLDatabase.from_uri(
        f"sqlite:///{db_path}"
    )


def get_sql_tools():
    """
    Return LangChain SQL database tools.
    """

    db = get_database()

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    toolkit = SQLDatabaseToolkit(
        db=db,
        llm=llm
    )

    return toolkit.get_tools()


__all__ = [
    "get_database",
    "get_sql_tools",
]