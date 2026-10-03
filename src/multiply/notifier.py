"""Pluggable notification channels: console, email and generic webhook.

No channel requires credentials to import or to run the console path, so the
package works out of the box for demos and tests. Email/webhook simply need
the relevant environment variables set; if they aren't, the dispatcher logs a
warning for that subscriber instead of crashing the whole notification run.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import urllib.request
from email.message import EmailMessage
from typing import Protocol

from .models import Subscriber

logger = logging.getLogger("multiply.notifier")


class NotConfiguredError(RuntimeError):
    """Raised by a channel that is missing required configuration."""


class Channel(Protocol):
    def send(self, subscriber: Subscriber, subject: str, body: str) -> None: ...


class ConsoleChannel:
    """Prints the notification. Always available; useful for demos/tests."""

    def __init__(self) -> None:
        self.sent: list[tuple[Subscriber, str, str]] = []

    def send(self, subscriber: Subscriber, subject: str, body: str) -> None:
        self.sent.append((subscriber, subject, body))
        print(f"[console -> {subscriber.name} ({subscriber.audience})] {subject}\n{body}\n")


class EmailChannel:
    """Sends via SMTP using SMTP_HOST/PORT/USER/PASSWORD/FROM env vars."""

    def send(self, subscriber: Subscriber, subject: str, body: str) -> None:
        host = os.environ.get("SMTP_HOST")
        sender = os.environ.get("SMTP_FROM")
        if not host or not sender:
            raise NotConfiguredError(
                "SMTP_HOST and SMTP_FROM must be set to send email notifications"
            )
        port = int(os.environ.get("SMTP_PORT", "587"))
        user = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = subscriber.contact
        msg.set_content(body)

        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)


class WebhookChannel:
    """POSTs a Slack/Discord-compatible JSON payload to the subscriber's URL."""

    def send(self, subscriber: Subscriber, subject: str, body: str) -> None:
        payload = json.dumps({"text": f"*{subject}*\n{body}"}).encode("utf-8")
        request = urllib.request.Request(
            subscriber.contact,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            if response.status >= 300:
                raise RuntimeError(f"webhook returned status {response.status}")


class NotificationDispatcher:
    """Routes each subscriber's notification to their configured channel.

    A failure for one subscriber (e.g. SMTP not configured) is logged and
    does not stop delivery to the rest of the list.
    """

    def __init__(self, channels: dict[str, Channel] | None = None) -> None:
        self.channels: dict[str, Channel] = channels or {
            "console": ConsoleChannel(),
            "email": EmailChannel(),
            "webhook": WebhookChannel(),
        }

    def dispatch(self, subscribers: list[Subscriber], subject: str, body_by_audience: dict[str, str]) -> None:
        for subscriber in subscribers:
            body = body_by_audience.get(subscriber.audience)
            if body is None:
                continue
            channel = self.channels.get(subscriber.channel)
            if channel is None:
                logger.warning("no channel registered for %r", subscriber.channel)
                continue
            try:
                channel.send(subscriber, subject, body)
            except Exception:
                logger.warning(
                    "failed to notify subscriber %s via %s", subscriber.id, subscriber.channel,
                    exc_info=True,
                )
