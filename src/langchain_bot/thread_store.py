from pathlib import Path
import json


THREADS_FILE = (
    Path(__file__).resolve()
    .parent.parent.parent
    / "chat_threads.json"
)


def load_threads(user_email):
    if not THREADS_FILE.exists():
        return []

    data = json.loads(
        THREADS_FILE.read_text()
    )

    return data.get(user_email, [])


def save_threads(user_email, threads):

    data = {}

    if THREADS_FILE.exists():
        data = json.loads(
            THREADS_FILE.read_text()
        )

    data[user_email] = threads

    THREADS_FILE.write_text(
        json.dumps(data, indent=2)
    )


def add_thread(
    user_email,
    conversation_id
):
    threads = load_threads(user_email)

    threads.append({
        "id": conversation_id,
        "label":
            f"Chat {conversation_id[:8]}"
    })

    save_threads(
        user_email,
        threads
    )