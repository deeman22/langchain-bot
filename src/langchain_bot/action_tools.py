from datetime import datetime
from pathlib import Path
import sqlite3

from langchain.tools import tool, ToolRuntime

from langchain_bot.context import SessionContext


DB_PATH = (
    Path(__file__).resolve()
    .parent.parent.parent
    / "ecommerce.db"
)


def _ts() -> str:
    return datetime.now().isoformat(
        timespec="seconds"
    )


def _thread_id(context: SessionContext) -> str:
    return (
        f"{context.user_email}:"
        f"{context.conversation_id}"
    )


@tool
def cancel_order_action(
    order_id: int,
    runtime: ToolRuntime[SessionContext]
) -> str:
    """
    Cancel an authenticated customer's order after admin approval.

    Only PLACED orders can be cancelled.
    """

    context = runtime.context

    user_email = context.user_email
    thread_id = _thread_id(context)

    now = _ts()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # Verify order ownership
        order = conn.execute(
            """
            SELECT
                o.id,
                o.user_id,
                o.status
            FROM orders o
            JOIN users u
                ON o.user_id = u.id
            WHERE o.id = ?
              AND u.email = ?
            """,
            (
                order_id,
                user_email
            )
        ).fetchone()

        if not order:
            return (
                f"Order #{order_id} was not found "
                "for the authenticated user."
            )

        if order["status"] != "PLACED":
            return (
                f"Order #{order_id} cannot be cancelled. "
                f"Current status is {order['status']}. "
                "Only PLACED orders can be cancelled."
            )

        # Cancel order
        conn.execute(
            """
            UPDATE orders
            SET status = 'CANCELLED'
            WHERE id = ?
            """,
            (order_id,)
        )

        # Refund payment
        conn.execute(
            """
            UPDATE payments
            SET status = 'REFUNDED'
            WHERE order_id = ?
            """,
            (order_id,)
        )

        # Audit/support ticket
        conn.execute(
            """
            INSERT INTO tickets (
                user_id,
                return_id,
                subject,
                status,
                thread_id,
                user_email,
                created_at,
                updated_at
            )
            VALUES (
                ?,
                NULL,
                ?,
                'RESOLVED',
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                order["user_id"],
                f"Cancellation completed for order #{order_id}",
                thread_id,
                user_email,
                now,
                now
            )
        )

        conn.commit()

    return (
        f"Order #{order_id} has been cancelled successfully. "
        "Its payment has been marked as REFUNDED."
    )


@tool
def create_return_action(
    order_id: int,
    product_name: str,
    reason: str,
    runtime: ToolRuntime[SessionContext]
) -> str:
    """
    Create a product return after admin approval.

    Only SHIPPED or DELIVERED orders can be returned.
    """

    context = runtime.context

    user_email = context.user_email
    thread_id = _thread_id(context)

    now = _ts()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # --------------------------------------------------
        # VERIFY ORDER OWNERSHIP
        # --------------------------------------------------

        order = conn.execute(
            """
            SELECT
                o.id,
                o.user_id,
                o.status
            FROM orders o
            JOIN users u
                ON o.user_id = u.id
            WHERE o.id = ?
              AND u.email = ?
            """,
            (
                order_id,
                user_email
            )
        ).fetchone()

        if not order:
            return (
                f"Order #{order_id} was not found "
                "for the authenticated user."
            )

        if order["status"] == "PLACED":
            return (
                f"Order #{order_id} has not shipped yet. "
                "Please cancel the order instead of creating a return."
            )

        if order["status"] not in (
            "SHIPPED",
            "DELIVERED"
        ):
            return (
                f"Order #{order_id} cannot be returned. "
                f"Current status is {order['status']}."
            )

        # --------------------------------------------------
        # FIND PRODUCT IN ORDER
        # --------------------------------------------------

        item = conn.execute(
            """
            SELECT
                oi.id AS order_item_id,
                oi.quantity,
                oi.unit_price,
                p.name AS product_name
            FROM order_items oi
            JOIN products p
                ON oi.product_id = p.id
            WHERE oi.order_id = ?
              AND LOWER(p.name) = LOWER(?)
            """,
            (
                order_id,
                product_name.strip()
            )
        ).fetchone()

        if not item:
            return (
                f"Product '{product_name}' was not found "
                f"in order #{order_id}."
            )

        # --------------------------------------------------
        # PREVENT DUPLICATE RETURN
        # --------------------------------------------------

        existing_return = conn.execute(
            """
            SELECT id, status
            FROM returns
            WHERE order_id = ?
              AND order_item_id = ?
              AND user_id = ?
              AND status IN ('PENDING', 'APPROVED')
            """,
            (
                order_id,
                item["order_item_id"],
                order["user_id"]
            )
        ).fetchone()

        if existing_return:
            return (
                "A return already exists for this item. "
                f"Return #{existing_return['id']} "
                f"is {existing_return['status']}."
            )

        # --------------------------------------------------
        # CREATE RETURN
        # --------------------------------------------------

        cursor = conn.execute(
            """
            INSERT INTO returns (
                order_id,
                order_item_id,
                user_id,
                reason,
                status,
                requested_at,
                resolved_at,
                admin_id
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                'APPROVED',
                ?,
                ?,
                NULL
            )
            """,
            (
                order_id,
                item["order_item_id"],
                order["user_id"],
                reason,
                now,
                now
            )
        )

        return_id = cursor.lastrowid

        # --------------------------------------------------
        # CREATE REFUND PAYMENT ENTRY
        # --------------------------------------------------

        original_payment = conn.execute(
            """
            SELECT
                payment_method
            FROM payments
            WHERE order_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (order_id,)
        ).fetchone()

        payment_method = (
            original_payment["payment_method"]
            if original_payment
            else "ORIGINAL_PAYMENT_METHOD"
        )

        refund_amount = (
            item["quantity"]
            * item["unit_price"]
        )

        conn.execute(
            """
            INSERT INTO payments (
                order_id,
                amount,
                status,
                payment_method,
                transaction_reference,
                paid_at
            )
            VALUES (
                ?,
                ?,
                'REFUNDED',
                ?,
                ?,
                ?
            )
            """,
            (
                order_id,
                refund_amount,
                payment_method,
                f"REFUND-RETURN-{return_id}",
                now
            )
        )

        # --------------------------------------------------
        # CREATE TICKET
        # --------------------------------------------------

        conn.execute(
            """
            INSERT INTO tickets (
                user_id,
                return_id,
                subject,
                status,
                thread_id,
                user_email,
                created_at,
                updated_at
            )
            VALUES (
                ?,
                ?,
                ?,
                'RESOLVED',
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                order["user_id"],
                return_id,
                (
                    f"Return completed for "
                    f"order #{order_id}: "
                    f"{item['product_name']}"
                ),
                thread_id,
                user_email,
                now,
                now
            )
        )

        conn.commit()

    return (
        f"Return #{return_id} was created for "
        f"'{item['product_name']}' from order #{order_id}. "
        f"Refund amount: {refund_amount:.2f}."
    )


def get_action_tools():
    return [
        cancel_order_action,
        create_return_action
    ]


__all__ = [
    "cancel_order_action",
    "create_return_action",
    "get_action_tools",
]