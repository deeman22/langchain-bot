import streamlit as st

from langchain_bot.auth import (
    authenticate_user
)

from langchain_bot.hitl_utils import (
    list_pending_actions,
    resume_with_decision,
)

from langchain_bot.gmail_tools import (
    initialize_gmail
)


def init_session():

    st.session_state.setdefault(
        "admin_email",
        None
    )


def extract_last_response(result):

    if not isinstance(result, dict):
        return str(result)

    messages = result.get(
        "messages",
        []
    )

    for msg in reversed(messages):

        if (
            getattr(msg, "type", None)
            == "ai"
            and getattr(msg, "content", None)
        ):
            return msg.content

    return "Action processed."


def admin_login():

    with st.form(
        "admin_login"
    ):

        email = st.text_input(
            "Admin Email"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        submitted = (
            st.form_submit_button(
                "Login"
            )
        )

        if submitted:

            user = authenticate_user(
                email=email,
                password=password,
                role="admin"
            )

            if not user:

                st.error(
                    "Invalid admin credentials."
                )

                return False

            st.session_state.admin_email = (
                user["email"]
            )

            st.rerun()

    return False


def main():

    st.set_page_config(
        page_title="Admin Approval Dashboard",
        page_icon="🛡️",
        layout="wide"
    )

    init_session()

    initialize_gmail()

    st.title(
        "🛡️ Human Approval Dashboard"
    )

    if not st.session_state.admin_email:

        admin_login()
        return

    st.sidebar.success(
        f"Admin: "
        f"{st.session_state.admin_email}"
    )

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    status_filter = st.sidebar.selectbox(
        "Status",
        [
            "PENDING",
            "APPROVED",
            "REJECTED",
            "ALL"
        ]
    )

    email_filter = st.sidebar.text_input(
        "Customer email filter"
    ).strip()

    actions = list_pending_actions(
        status=status_filter,
        email=(
            email_filter
            if email_filter
            else None
        )
    )

    st.subheader(
        f"Actions ({len(actions)})"
    )

    if not actions:

        st.info(
            "No matching actions."
        )

        return

    # --------------------------------------------------
    # ACTION CARDS
    # --------------------------------------------------

    for action in actions:

        title = (
            f"#{action['id']} | "
            f"{action['action_type']} | "
            f"Order #{action['order_id']}"
        )

        with st.expander(
            title,
            expanded=(
                action["status"]
                == "PENDING"
            )
        ):

            st.write(
                "**Customer:**",
                action["user_email"]
            )

            st.write(
                "**Order:**",
                action["order_id"]
            )

            st.write(
                "**Action:**",
                action["action_type"]
            )

            st.write(
                "**Thread:**",
                action["thread_id"]
            )

            st.write(
                "**Status:**",
                action["status"]
            )

            if action.get(
                "product_name"
            ):

                st.write(
                    "**Product:**",
                    action["product_name"]
                )

            if action.get("reason"):

                st.write(
                    "**Reason:**",
                    action["reason"]
                )

            st.write(
                "**Created:**",
                action["created_at"]
            )

            if (
                action["status"]
                != "PENDING"
            ):
                continue

            approve_col, reject_col = (
                st.columns(2)
            )

            # ------------------------------------------
            # APPROVE
            # ------------------------------------------

            with approve_col:

                if st.button(
                    "✅ Approve",
                    key=(
                        f"approve_"
                        f"{action['id']}"
                    )
                ):

                    try:

                        with st.spinner(
                            "Approving..."
                        ):

                            result = (
                                resume_with_decision(
                                    thread_id=(
                                        action[
                                            "thread_id"
                                        ]
                                    ),
                                    decision="approve",
                                    pending_action_id=(
                                        action["id"]
                                    )
                                )
                            )

                        st.success(
                            extract_last_response(
                                result
                            )
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Approval failed: {e}"
                        )

            # ------------------------------------------
            # REJECT
            # ------------------------------------------

            with reject_col:

                if st.button(
                    "❌ Reject",
                    key=(
                        f"reject_"
                        f"{action['id']}"
                    )
                ):

                    try:

                        with st.spinner(
                            "Rejecting..."
                        ):

                            result = (
                                resume_with_decision(
                                    thread_id=(
                                        action[
                                            "thread_id"
                                        ]
                                    ),
                                    decision="reject",
                                    pending_action_id=(
                                        action["id"]
                                    ),
                                    rejection_message=(
                                        "The administrator "
                                        "rejected this request."
                                    )
                                )
                            )

                        st.warning(
                            extract_last_response(
                                result
                            )
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Rejection failed: {e}"
                        )


if __name__ == "__main__":
    main()