from datetime import datetime
from pathlib import Path
import sqlite3

from langgraph.types import Command

from langchain_bot.agent import get_agent
from langchain_bot.context import SessionContext


DB_PATH = (
    Path(__file__).resolve()
    .parent.parent.parent
    / "ecommerce.db"
)


def _ts():
    return datetime.now().isoformat(
        timespec="seconds"
    )


def _config_from_thread_id(
    thread_id: str
):

    return {
        "configurable": {
            "thread_id": thread_id
        },
        "recursion_limit": 20
    }


def _split_thread_id(
    thread_id: str
):

    user_email, conversation_id = (
        thread_id.split(":", 1)
    )

    return (
        user_email,
        conversation_id
    )


def get_pending_action_for_thread(
    thread_id: str
):

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT *
            FROM pending_actions
            WHERE thread_id = ?
            AND status = 'PENDING'
            ORDER BY id DESC
            LIMIT 1
            """,
            (thread_id,)
        ).fetchone()

        return dict(row) if row else None


def list_pending_actions(
    status: str | None = "PENDING",
    email: str | None = None
):

    sql = """
        SELECT *
        FROM pending_actions
        WHERE 1 = 1
    """

    params = []

    if status and status != "ALL":
        sql += " AND status = ?"
        params.append(status)

    if email:
        sql += " AND user_email = ?"
        params.append(email)

    sql += " ORDER BY created_at DESC"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            sql,
            params
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def handle_interrupt(
    result,
    user_email: str,
    conversation_id: str
):
    """
    Inspect an agent result for HITL interrupts.

    If present, store the requested business action
    in pending_actions.
    """

    if not isinstance(result, dict):
        return None

    interrupts = result.get(
        "__interrupt__"
    )

    if not interrupts:
        return None

    thread_id = (
        f"{user_email}:{conversation_id}"
    )

    notices = []

    for interrupt_obj in interrupts:

        value = getattr(
            interrupt_obj,
            "value",
            None
        )

        if not value:
            continue

        action_requests = value.get(
            "action_requests",
            []
        )

        for action in action_requests:

            tool_name = action.get("name")
            args = action.get(
                "args",
                {}
            )

            if tool_name == "cancel_order_action":

                action_type = (
                    "CANCEL_ORDER"
                )

            elif tool_name == "create_return_action":

                action_type = (
                    "CREATE_RETURN"
                )

            else:
                continue

            order_id = args.get(
                "order_id"
            )

            product_name = args.get(
                "product_name"
            )

            reason = args.get(
                "reason"
            )

            # ------------------------------------------
            # DEDUPE
            # ------------------------------------------

            existing = (
                get_pending_action_for_thread(
                    thread_id
                )
            )

            if existing:

                notices.append(
                    "⏳ **Request already pending approval**\n\n"
                    f"Action: `{existing['action_type']}`  \n"
                    f"Order: `#{existing['order_id']}`"
                )

                continue

            now = _ts()

            with sqlite3.connect(DB_PATH) as conn:

                conn.execute(
                    """
                    INSERT INTO pending_actions (
                        thread_id,
                        user_email,
                        action_type,
                        order_id,
                        product_name,
                        reason,
                        status,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        'PENDING',
                        ?,
                        ?
                    )
                    """,
                    (
                        thread_id,
                        user_email,
                        action_type,
                        order_id,
                        product_name,
                        reason,
                        now,
                        now
                    )
                )

                conn.commit()

            if action_type == "CANCEL_ORDER":

                notices.append(
                    "⏳ **Cancellation awaiting admin approval**\n\n"
                    f"Order: `#{order_id}`"
                )

            else:

                notices.append(
                    "⏳ **Return awaiting admin approval**\n\n"
                    f"Order: `#{order_id}`  \n"
                    f"Product: `{product_name}`  \n"
                    f"Reason: {reason}"
                )

    if not notices:
        return None

    return "\n\n".join(notices)


def resume_with_decision(
    thread_id: str,
    decision: str,
    pending_action_id: int | None = None,
    rejection_message: str | None = None
):
    """
    Resume the paused LangGraph thread.

    decision must be 'approve' or 'reject'.
    """

    if decision not in (
        "approve",
        "reject"
    ):
        raise ValueError(
            "decision must be approve or reject"
        )

    user_email, conversation_id = (
        _split_thread_id(thread_id)
    )

    config = _config_from_thread_id(
        thread_id
    )

    context = SessionContext(
        user_email=user_email,
        conversation_id=conversation_id,
        role="customer"
    )

    if decision == "approve":

        decision_payload = {
            "type": "approve"
        }

        new_status = "APPROVED"

    else:

        decision_payload = {
            "type": "reject",
            "message": (
                rejection_message
                or
                "The admin rejected this request. "
                "Do not retry the action automatically."
            )
        }

        new_status = "REJECTED"

    # Resume SAME paused graph thread
    result = get_agent().invoke(
        Command(
            resume={
                "decisions": [
                    decision_payload
                ]
            }
        ),
        config=config,
        context=context
    )

    now = _ts()

    with sqlite3.connect(DB_PATH) as conn:

        if pending_action_id is not None:

            conn.execute(
                """
                UPDATE pending_actions
                SET status = ?,
                    updated_at = ?
                WHERE id = ?
                AND status = 'PENDING'
                """,
                (
                    new_status,
                    now,
                    pending_action_id
                )
            )

        else:

            conn.execute(
                """
                UPDATE pending_actions
                SET status = ?,
                    updated_at = ?
                WHERE thread_id = ?
                AND status = 'PENDING'
                """,
                (
                    new_status,
                    now,
                    thread_id
                )
            )

        conn.commit()

    return result


__all__ = [
    "handle_interrupt",
    "resume_with_decision",
    "list_pending_actions",
    "get_pending_action_for_thread",
]