import streamlit as st
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def get_llm():
    """
    Create and return the LLM instance.
    """
    return ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.3
    )


def build_chain(llm):
    """
    Build the prompt template and connect it to the LLM.
    """
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a concise, helpful assistant. "
            "Use prior chat history to stay on context."
        ),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])

    return prompt | llm


def init_session():
    """
    Initialize chat history in session state.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = [
            AIMessage(content="Hi! Ask me anything.")
        ]


def render_history():
    """
    Render all messages stored in session state.
    """
    for msg in st.session_state.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"

        with st.chat_message(role):
            st.markdown(msg.content)


def chat_round(llm, user_input):
    """
    Execute one chat round.
    """
    print("\n" + "=" * 50)
    print("USER INPUT")
    print("=" * 50)
    print(user_input)

    st.session_state.messages.append(
        HumanMessage(content=user_input)
    )

    print("\nCURRENT HISTORY")
    print("=" * 50)

    for i, msg in enumerate(st.session_state.messages):
        print(f"{i + 1}. {msg.__class__.__name__}: {msg.content}")

    chain = build_chain(llm)

    payload = {
        "input": user_input,
        "history": st.session_state.messages
    }

    # print("\nCHAIN INPUT")
    # print("=" * 50)
    # print(payload)

    response = chain.invoke(payload)

    # print("\nLLM RESPONSE")
    # print("=" * 50)
    # print(response.content)

    st.session_state.messages.append(response)

    # print("\nUPDATED HISTORY")
    # print("=" * 50)

    # for i, msg in enumerate(st.session_state.messages):
    #     print(f"{i + 1}. {msg.__class__.__name__}: {msg.content}")

    # print("=" * 50 + "\n")



def main():
    st.set_page_config(
        page_title="LangChain Bot",
        page_icon="🤖"
    )

    st.title("LangChain Bot")
    st.caption("A simple conversational assistant built with LangChain and Streamlit.")

    load_dotenv()

    init_session()
    render_history()

    prompt = st.chat_input("Ask a question")

    if prompt:
        llm = get_llm()

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                chat_round(llm, prompt)

        st.rerun()


if __name__ == "__main__":
    main()