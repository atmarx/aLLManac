"""Notifications — telling a person their ticket moved.

Two channels, because there are two audiences:

  * the PERSON who filed something — an email, since only they should see
    it.  With no SMTP server configured it is appended to the outbox file
    on the state volume instead, which is the home-lab answer: nothing is
    lost, and `tail` is the inbox.
  * the DESK — the platform admins as a group.  A webhook if one is set
    (a Teams Workflows URL, or anything that takes {"text": ...}); else an
    email to the `admins:` list, which falls back to the outbox the same way.

**A notification is a pointer, not the content.**  What goes to the desk is
the envelope — ticket id, kind, name, who, term — and where to read the
rest.  Never the purpose, the details, the thread, or a problem report's
text: those were typed into the platform, and a webhook is somebody else's
cloud.  Same line as "The census stops at the envelope" in
docs/design-walls.md.  The one thing that does travel in full is an admin's
note to a requester, which the admin wrote knowing it would be sent.

Best effort, always.  A mail relay that is down must never fail the tool
call that tried to use it — the ticket is on disk either way, and the
queue is where the truth lives.  Every send returns a short status the
caller can show an admin, and failures go to stderr for `just logs`.

No sibling planes: the caller passes the addresses.  Config only.
"""

import asyncio
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.message import EmailMessage

import httpx

from .config import (
    NOTIFY_WEBHOOK_FORMAT,
    NOTIFY_WEBHOOK_URL,
    OUTBOX_PATH,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TLS,
    SMTP_USER,
)

TIMEOUT = 10


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _outbox(to: list[str], subject: str, body: str) -> str:
    with open(OUTBOX_PATH, "a") as f:
        f.write(f"=== {_now()}\nTo: {', '.join(to)}\nSubject: {subject}\n\n"
                f"{body.rstrip()}\n\n")
    return "written to the outbox (no SMTP server set)"


def _smtp(to: list[str], subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body)
    if SMTP_TLS == "ssl":
        s = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT,
                             context=ssl.create_default_context())
    else:
        s = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT)
    with s:
        if SMTP_TLS == "starttls":
            s.starttls(context=ssl.create_default_context())
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASSWORD)
        s.send_message(msg)


def email(to: list[str], subject: str, body: str) -> str:
    """-> a short status for the caller.  Never raises."""
    to = sorted({t for t in to if t})
    if not to:
        return "no one to email"
    try:
        if not SMTP_HOST:
            return _outbox(to, subject, body)
        _smtp(to, subject, body)
        return f"emailed {', '.join(to)}"
    except Exception as e:
        print(f"notify: email to {to} failed: {type(e).__name__}: {e}",
              file=sys.stderr)
        try:
            _outbox(to, subject, body)
            return f"email failed ({type(e).__name__}); kept in the outbox"
        except Exception:
            return f"email failed ({type(e).__name__})"


def _teams(title: str, lines: list[str], link: str) -> dict:
    """A Teams Workflows payload: one Adaptive Card.  The old Office 365
    connector URLs accept the same shape, so it serves either."""
    body = [{"type": "TextBlock", "text": title, "weight": "Bolder",
             "size": "Medium", "wrap": True}]
    body += [{"type": "TextBlock", "text": ln, "wrap": True, "spacing": "Small"}
             for ln in lines]
    card = {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard", "version": "1.4", "body": body}
    if link:
        card["actions"] = [{"type": "Action.OpenUrl", "title": "Open the desk",
                            "url": link}]
    return {"type": "message", "attachments": [
        {"contentType": "application/vnd.microsoft.card.adaptive",
         "content": card}]}


async def webhook(title: str, lines: list[str], link: str = "") -> str:
    try:
        if NOTIFY_WEBHOOK_FORMAT == "text":
            payload = {"text": "\n".join([title, *lines,
                                          *([link] if link else [])])}
        else:
            payload = _teams(title, lines, link)
        async with httpx.AsyncClient(timeout=TIMEOUT) as cx:
            r = await cx.post(NOTIFY_WEBHOOK_URL, json=payload)
            r.raise_for_status()
        return "posted to the desk channel"
    except Exception as e:
        # The URL is a credential (anyone holding it can post), so it is
        # never printed — only what went wrong.
        print(f"notify: webhook failed: {type(e).__name__}", file=sys.stderr)
        return f"desk webhook failed ({type(e).__name__})"


async def desk(admins: list[str], title: str, lines: list[str],
               link: str = "", email_fallback: bool = True) -> str:
    """Tell the platform admins.  Webhook if configured, else email — unless
    the caller says this one is channel chatter (a decision someone on the
    desk just made), which isn't worth an email to everyone."""
    if NOTIFY_WEBHOOK_URL:
        return await webhook(title, lines, link)
    if not email_fallback:
        return ""
    body = "\n".join([*lines, "", link]).strip() + "\n"
    return await asyncio.to_thread(email, admins, f"[aLLManac] {title}", body)


async def person(to: list[str], subject: str, body: str) -> str:
    return await asyncio.to_thread(email, to, f"[aLLManac] {subject}", body)


def configured() -> dict:
    """What's set, for the operator — never the values that are secrets."""
    return {"smtp": f"{SMTP_HOST}:{SMTP_PORT} ({SMTP_TLS}"
                    f"{', auth' if SMTP_USER else ', no auth'})" if SMTP_HOST
                    else f"none — mail goes to {OUTBOX_PATH}",
            "webhook": NOTIFY_WEBHOOK_FORMAT if NOTIFY_WEBHOOK_URL
                       else "none — the desk is emailed"}
