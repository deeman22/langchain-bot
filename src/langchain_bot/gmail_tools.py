from pathlib import Path
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from langchain_google_community.gmail.send_message import (
    GmailSendMessage
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

_gmail_service = None


def get_gmail_service():
    global _gmail_service

    if _gmail_service:
        return _gmail_service

    root = (
        Path(__file__).resolve()
        .parent.parent.parent
    )

    credentials_file = (
        root / "credentials.json"
    )

    token_file = (
        root / "token.pickle"
    )

    creds = None

    if token_file.exists():
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    elif not creds:

        flow = (
            InstalledAppFlow
            .from_client_secrets_file(
                str(credentials_file),
                SCOPES
            )
        )

        creds = flow.run_local_server(
            port=0
        )

        with open(token_file, "wb") as f:
            pickle.dump(creds, f)

    _gmail_service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    return _gmail_service


def initialize_gmail() -> bool:
    try:
        get_gmail_service()
        return True

    except Exception as e:
        print(
            f"Gmail unavailable: {e}"
        )
        return False


def get_gmail_tools():

    try:
        service = get_gmail_service()

        return [
            GmailSendMessage(
                api_resource=service
            )
        ]

    except Exception:
        return []


def is_gmail_available():

    return _gmail_service is not None