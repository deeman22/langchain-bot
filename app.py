import streamlit as st
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from uuid import uuid4
from langchain_bot.auth import authenticate_user


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


# def init_session():
#     """
#     Initialize chat history in session state.
#     """
#     if "messages" not in st.session_state:
#         st.session_state.messages = [
#             AIMessage(content="Hi! Ask me anything.")
#         ]

def init_session():
    st.session_state.setdefault("conversations", {})
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("user_email", None)
    st.session_state.setdefault("user_role", None)
    st.session_state.setdefault("conversation_id", None)


def render_history():
    """
    Render all messages stored in session state.
    """
    for msg in st.session_state.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"

        with st.chat_message(role):
            st.markdown(msg.content)


def start_new_conversation():
    conversation_id = str(uuid4())

    messages = [
        AIMessage(content="Hi! Ask me anything.")
    ]

    st.session_state.conversation_id = conversation_id
    st.session_state.messages = messages

    st.session_state.conversations[
        conversation_id
    ] = messages.copy()


def load_conversation(conv_id):
    if conv_id in st.session_state.conversations:

        st.session_state.conversation_id = conv_id

        st.session_state.messages = (
            st.session_state.conversations[conv_id].copy()
        )

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

    response = chain.invoke(payload)
    st.session_state.messages.append(response)
    
    if st.session_state.conversation_id:
        st.session_state.conversations[
            st.session_state.conversation_id
        ] = st.session_state.messages.copy()



def main():
    st.set_page_config(
        page_title="LangChain Bot",
        page_icon="🤖"
    )

    st.title("LangChain Bot")
    st.caption(
        "A simple conversational assistant built with LangChain and Streamlit."
    )

    load_dotenv()

    init_session()

    user_email = st.session_state.user_email

    # ------------------------
    # LOGIN SCREEN
    # ------------------------
    if not user_email:

        with st.form("login_form"):

            email = st.text_input("Email")

            password = st.text_input(
                "Password",
                type="password"
            )

            role = st.selectbox(
                "Role",
                ["customer", "admin"]
            )

            submitted = st.form_submit_button(
                "Login"
            )

            if submitted:

                user = authenticate_user(
                    email=email,
                    password=password,
                    role=role
                )

                if user:

                    st.session_state.user_email = (
                        user["email"]
                    )

                    st.session_state.user_role = (
                        user["role"]
                    )

                    # Step 6.2.7
                    start_new_conversation()

                    st.success(
                        f"Welcome {user['full_name']}"
                    )

                    st.rerun()

                else:
                    st.error(
                        "Invalid email/password"
                    )

        return

    # ------------------------
    # SIDEBAR
    # ------------------------
    st.sidebar.header("Conversations")

    if st.sidebar.button(
        "Start new conversation"
    ):
        start_new_conversation()
        st.rerun()

    conversation_ids = list(
        st.session_state.conversations.keys()
    )

    if conversation_ids:

        selected_conv = st.sidebar.selectbox(
            "Select Conversation",
            conversation_ids,
            index=conversation_ids.index(
                st.session_state.conversation_id
            )
            if st.session_state.conversation_id
            in conversation_ids
            else 0
        )

        if (
            selected_conv
            != st.session_state.conversation_id
        ):
            load_conversation(selected_conv)
            st.rerun()

    else:
        st.sidebar.selectbox(
            "Select Conversation",
            ["(no threads yet)"]
        )

    # ------------------------
    # USER INFO
    # ------------------------
    st.info(
        f"Logged in as: "
        f"{st.session_state.user_email} | "
        f"Role: {st.session_state.user_role} | "
        f"Conversation: "
        f"{st.session_state.conversation_id or '—'}"
    )

    render_history()

    prompt = st.chat_input(
        "Ask a question"
    )

    if prompt:

        llm = get_llm()

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                chat_round(
                    llm,
                    prompt
                )

        st.rerun()


if __name__ == "__main__":
    main()