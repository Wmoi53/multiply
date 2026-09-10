# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "google-api-python-client",
#   "google-auth-httplib2",
#   "google-auth-oauthlib",
#   "transformers>=4.40",
#   "torch",
#   "accelerate",
# ]
# ///
"""
Scan Gmail for unread messages with an audio attachment (voicemail, voice
memo, etc.), transcribe each with openai/whisper-large-v3, and save a draft
reply containing the transcript.

One-time setup:
1. In Google Cloud Console, create a project, enable the "Gmail API", and
   create OAuth 2.0 credentials of type "Desktop app". Download the JSON
   and save it next to this script as `credentials.json`.
2. pip install google-api-python-client google-auth-httplib2
   google-auth-oauthlib transformers torch accelerate
3. Run this script once locally: it opens a browser for you to grant Gmail
   access, then caches a `token.json` so future runs are non-interactive.

Usage:
    python agent/gmail_voice_transcribe.py
    python agent/gmail_voice_transcribe.py --query "is:unread has:attachment newer_than:7d"
"""

import argparse
import base64
import mimetypes
import os
import tempfile
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from whisper_transcribe import transcribe

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
DEFAULT_QUERY = "is:unread has:attachment (filename:mp3 OR filename:wav OR filename:m4a OR filename:ogg)"
TRANSCRIBED_LABEL = "Transcribed"


def get_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def get_or_create_label(service, name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == name:
            return label["id"]
    created = (
        service.users()
        .labels()
        .create(userId="me", body={"name": name, "labelListVisibility": "labelShow"})
        .execute()
    )
    return created["id"]


def find_audio_attachments(payload, out: list) -> None:
    mime_type = payload.get("mimeType", "")
    filename = payload.get("filename", "")
    body = payload.get("body", {})
    if filename and (mime_type.startswith("audio/") or filename.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))):
        out.append({"filename": filename, "attachmentId": body.get("attachmentId"), "mimeType": mime_type})
    for part in payload.get("parts", []) or []:
        find_audio_attachments(part, out)


def download_attachment(service, message_id: str, attachment_id: str, filename: str) -> str:
    attachment = (
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
    )
    data = base64.urlsafe_b64decode(attachment["data"])
    suffix = os.path.splitext(filename)[1] or mimetypes.guess_extension("audio/mpeg") or ".bin"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def create_draft_reply(service, message: dict, transcript: str) -> None:
    thread_id = message["threadId"]
    headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
    to_addr = headers.get("From", "")
    subject = headers.get("Subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    body = MIMEText(f"Transcript (via openai/whisper-large-v3):\n\n{transcript}")
    body["to"] = to_addr
    body["subject"] = subject
    body["In-Reply-To"] = headers.get("Message-ID", "")
    body["References"] = headers.get("Message-ID", "")
    raw = base64.urlsafe_b64encode(body.as_bytes()).decode()

    service.users().drafts().create(
        userId="me", body={"message": {"raw": raw, "threadId": thread_id}}
    ).execute()


def process_message(service, message_id: str, label_id: str, hosted: bool) -> None:
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    attachments: list = []
    find_audio_attachments(message["payload"], attachments)
    if not attachments:
        return

    for att in attachments:
        if not att["attachmentId"]:
            continue
        path = download_attachment(service, message_id, att["attachmentId"], att["filename"])
        try:
            transcript = transcribe(path, hosted=hosted)
        finally:
            os.remove(path)
        create_draft_reply(service, message, transcript)
        print(f"[{message_id}] transcribed {att['filename']}: {transcript[:80]}...")

    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [label_id], "removeLabelIds": ["UNREAD"]}
    ).execute()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Gmail search query for candidate messages")
    parser.add_argument("--hosted", action="store_true", help="Use HF Inference API instead of a local model")
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args()

    service = get_service()
    label_id = get_or_create_label(service, TRANSCRIBED_LABEL)

    results = (
        service.users()
        .messages()
        .list(userId="me", q=args.query, maxResults=args.max_results)
        .execute()
    )
    messages = results.get("messages", [])
    if not messages:
        print("No matching messages.")
        return

    for m in messages:
        process_message(service, m["id"], label_id, hosted=args.hosted)


if __name__ == "__main__":
    main()
