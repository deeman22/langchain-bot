from pathlib import Path
import sqlite3


ROOT_DIR = Path(__file__).resolve().parents[2]

DB_PATH = ROOT_DIR / "ecommerce.db"
SQL_SEED_PATH = ROOT_DIR / "ecommerce_setup.sql"


def init_database():
    """
    Create and seed the SQLite database.
    """

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    sql_script = SQL_SEED_PATH.read_text(
        encoding="utf-8"
    )

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.executescript(sql_script)
        conn.commit()
    finally:
        conn.close()

    return DB_PATH


def main():
    db_path = init_database()
    print(f"Database initialized at: {db_path}")


if __name__ == "__main__":
    main()