import streamlit as st
from dotenv import load_dotenv
from uuid import uuid4

from langchain_bot.auth import authenticate_user
from langchain_bot.agent import get_agent,get_thread_config,reset_agent
from langchain_bot.rag_tool import initialize_vector_store
from langchain_bot.thread_store import load_threads, add_thread
from langchain_bot.gmail_tools import initialize_gmail,is_gmail_available
from langchain_bot.context import SessionContext




def init_session():
    """Initialize Streamlit session state."""

    st.session_state.setdefault(
        "user_email",
        None
    )

    st.session_state.setdefault(
        "user_role",
        None
    )

    st.session_state.setdefault(
        "conversation_id",
        None
    )

    st.session_state.setdefault(
        "vector_store_ready",
        False
    )


def render_history():
    """
    Load and render conversation history from
    LangGraph checkpointer.
    """

    if (
        not st.session_state.user_email
        or not st.session_state.conversation_id
    ):
        return

    config = get_thread_config(
        st.session_state.user_email,
        st.session_state.conversation_id
    )

    snapshot = get_agent().get_state(config)

    messages = snapshot.values.get(
        "messages",
        []
    )

    for msg in messages:

        # Human message
        if msg.type == "human":

            with st.chat_message("user"):
                st.markdown(msg.content)

        # AI message
        elif msg.type == "ai" and msg.content:

            with st.chat_message("assistant"):
                st.markdown(msg.content)


def start_new_conversation():
    """
    Create a new conversation thread.
    Only the conversation ID is stored in JSON.
    """

    conversation_id = str(uuid4())

    add_thread(
        st.session_state.user_email,
        conversation_id
    )

    st.session_state.conversation_id = (
        conversation_id
    )


def chat_round(user_input):
    """
    Send a new user message to the agent.

    Conversation history is managed by the
    LangGraph checkpointer.
    """

    config = get_thread_config(
        st.session_state.user_email,
        st.session_state.conversation_id
    )
    
    context = SessionContext(
        user_email=st.session_state.user_email,
        conversation_id=st.session_state.conversation_id,
        role=st.session_state.user_role
    )

    get_agent().invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_input
                }
            ]
        },
        config=config,
        context=context
    )


def main():

    st.set_page_config(
        page_title="LangChain Bot",
        page_icon="🤖"
    )

    load_dotenv()

    st.title("LangChain Bot")
    st.caption(
        "A conversational e-commerce support assistant."
    )

    init_session()

    # --------------------------------------------------
    # INITIALIZE KNOWLEDGE BASE
    # --------------------------------------------------

    if not st.session_state.vector_store_ready:

        try:

            with st.spinner(
                "Initializing knowledge base..."
            ):
                initialize_vector_store()

            st.session_state.vector_store_ready = True

        except Exception as e:

            st.error(
                f"Knowledge base initialization failed: {e}"
            )

            st.stop()


    # GMAIL READINESS
    gmail_ready = initialize_gmail()

    if gmail_ready:
        reset_agent()

    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------

    if not st.session_state.user_email:

        with st.form("login_form"):

            email = st.text_input(
                "Email"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            role = st.selectbox(
                "Role",
                [
                    "customer",
                    "admin"
                ]
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

                    # Save logged-in user
                    st.session_state.user_email = (
                        user["email"]
                    )

                    st.session_state.user_role = (
                        user["role"]
                    )

                    # Load existing threads
                    threads = load_threads(
                        user["email"]
                    )

                    if threads:

                        # Open first existing conversation
                        st.session_state.conversation_id = (
                            threads[0]["id"]
                        )

                    else:

                        # First login -> create thread
                        conversation_id = str(uuid4())

                        add_thread(
                            user["email"],
                            conversation_id
                        )

                        st.session_state.conversation_id = (
                            conversation_id
                        )

                    st.success(
                        f"Welcome {user['full_name']}"
                    )

                    st.rerun()

                else:

                    st.error(
                        "Invalid email/password"
                    )

        return

    # --------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------

    st.sidebar.header("Conversations")

    #Gmail
    if is_gmail_available():
        st.sidebar.success(
            "📧 Gmail Enabled"
        )
    else:
        st.sidebar.warning(
            "📧 Gmail Not Configured"
        )
    
    
    # Start new conversation
    if st.sidebar.button(
        "Start new conversation"
    ):

        start_new_conversation()
        st.rerun()

    # Load thread IDs for current user
    threads = load_threads(
        st.session_state.user_email
    )

    conversation_ids = [
        thread["id"]
        for thread in threads
    ]

    if conversation_ids:

        current_index = 0

        if (
            st.session_state.conversation_id
            in conversation_ids
        ):
            current_index = conversation_ids.index(
                st.session_state.conversation_id
            )

        selected_conv = st.sidebar.selectbox(
            "Select Conversation",
            conversation_ids,
            index=current_index
        )

        # User selected another conversation
        if (
            selected_conv
            != st.session_state.conversation_id
        ):

            st.session_state.conversation_id = (
                selected_conv
            )

            st.rerun()

    else:

        st.sidebar.write(
            "(no threads yet)"
        )

    # --------------------------------------------------
    # USER INFO
    # --------------------------------------------------

    st.info(
        f"Logged in as: "
        f"{st.session_state.user_email} | "
        f"Role: "
        f"{st.session_state.user_role} | "
        f"Conversation: "
        f"{st.session_state.conversation_id or '—'}"
    )

    # --------------------------------------------------
    # CHAT HISTORY
    # --------------------------------------------------

    render_history()

    # --------------------------------------------------
    # CHAT INPUT
    # --------------------------------------------------

    prompt = st.chat_input(
        "Ask a question"
    )

    if prompt:

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Thinking..."):
            chat_round(prompt)

        st.rerun()


if __name__ == "__main__":
    main()