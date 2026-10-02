from pathlib import Path
from typing import TypedDict
import sqlite3


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "ecommerce.db"


class UserRecord(TypedDict):
    email: str
    full_name: str
    role: str


def authenticate_user(
    email: str,
    password: str,
    role: str | None = None
) -> UserRecord | None:

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        if role:
            cursor.execute(
                """
                SELECT email, full_name, role
                FROM users
                WHERE email = ?
                AND password = ?
                AND role = ?
                """,
                (email, password, role)
            )
        else:
            cursor.execute(
                """
                SELECT email, full_name, role
                FROM users
                WHERE email = ?
                AND password = ?
                """,
                (email, password)
            )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"]
        }

    finally:
        conn.close()