from pathlib import Path

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
load_dotenv()

# Singleton cache
_vector_store = None


def load_policy_documents() -> list[Document]:
    """
    Load all policy text files from policies/ directory.
    """

    policies_dir = (
        Path(__file__).resolve()
        .parent.parent.parent
        / "policies"
    )

    documents: list[Document] = []

    for file_path in policies_dir.glob("*.txt"):

        loader = TextLoader(
            str(file_path),
            encoding="utf-8"
        )

        docs = loader.load()

        for doc in docs:
            doc.metadata["source"] = file_path.name

        documents.extend(docs)

    return documents


def split_documents(
    documents: list[Document]
) -> list[Document]:
    """
    Split policy documents into retrieval-friendly chunks.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    return splitter.split_documents(documents)


def get_vector_store():
    """
    Load or create Chroma vector store.
    """

    global _vector_store

    if _vector_store is not None:
        return _vector_store

    project_root = (
        Path(__file__).resolve()
        .parent.parent.parent
    )

    persist_dir = project_root / "chroma_db"

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    if (
        persist_dir.exists()
        and any(persist_dir.iterdir())
    ):
        print("Loading existing Chroma DB...")

        _vector_store = Chroma(
            persist_directory=str(persist_dir),
            embedding_function=embeddings
        )

        print("Loaded existing Chroma DB")

        return _vector_store

    print("Creating Chroma DB...")

    documents = load_policy_documents()

    chunks = split_documents(documents)

    _vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(persist_dir)
    )

    print(
        f"Indexed {len(chunks)} chunks into Chroma DB"
    )

    return _vector_store


@tool
def search_policies(query: str) -> str:
    """
    Search company policies and FAQs.
    Use this tool only for policy or FAQ questions.
    Do not use for user-specific orders or account data.
    """

    vector_store = get_vector_store()

    results = vector_store.similarity_search(
        query,
        k=4
    )

    if not results:
        return "No policy information found."

    formatted_results = []

    for doc in results:

        source = doc.metadata.get(
            "source",
            "unknown"
        )

        formatted_results.append(
            f"[Source: {source}]\n"
            f"{doc.page_content}"
        )

    return "\n\n---\n\n".join(
        formatted_results
    )


def initialize_vector_store():
    """
    Warm up vector store at application startup.
    """

    get_vector_store()


__all__ = [
    "search_policies",
    "initialize_vector_store",
]