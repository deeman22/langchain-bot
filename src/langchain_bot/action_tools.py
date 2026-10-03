from langchain.tools import tool, ToolRuntime
from langchain_bot.context import SessionContext
import sqlite3


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "ecommerce.db"


@tool
def cancel_order_action(
    order_id: int,
    runtime: ToolRuntime[SessionContext]
) -> str:
    """Cancel an order after admin approval."""

    user_email = runtime.context.user_email

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # verify ownership
    cur.execute("""
        SELECT o.id, o.status
        FROM orders o
        JOIN users u
            ON o.user_id = u.id
        WHERE o.id = ?
        AND u.email = ?
    """, (order_id, user_email))

    row = cur.fetchone()

    if not row:
        return "Order not found."

    if row[1] != "PLACED":
        return (
            "Order cannot be cancelled. "
            "Only PLACED orders can be cancelled."
        )

    cur.execute("""
        UPDATE orders
        SET status='CANCELLED'
        WHERE id=?
    """, (order_id,))

    cur.execute("""
        UPDATE payments
        SET status='REFUNDED'
        WHERE order_id=?
    """, (order_id,))

    conn.commit()
    conn.close()

    return f"Order {order_id} cancelled successfully."


@tool
def create_return_action(
    order_id: int,
    product_name: str,
    reason: str,
    runtime: ToolRuntime[SessionContext]
) -> str:
    """Create a return request after admin approval."""
    
def get_action_tools():
    return [
        cancel_order_action,
        create_return_action
    ]