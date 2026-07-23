"""Gmail implementation of :class:`EmailProvider`.

Auth uses the OAuth "installed app" (desktop) flow: on first run a browser consent is
required; the resulting token is cached and silently refreshed thereafter. All access is
read-only in Phase 1 (scope ``gmail.readonly``).
"""

from __future__ import annotations

import base64
import html
import re
from collections.abc import Iterator
from email.utils import getaddresses

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ...config import Settings, get_settings
from .base import EmailMessage, EmailProvider, HistoryChanges

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]*\n[ \t\n]*")


class GmailProvider(EmailProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._service = None  # lazily built after authentication

    # -- Auth ---------------------------------------------------------------
    def authenticate(self) -> None:
        """Load cached creds, refresh if stale, or run the interactive login once."""
        settings = self.settings
        creds: Credentials | None = None
        token_path = settings.google_token_path

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path), settings.gmail_scopes
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())  # silent refresh, no browser
            else:
                if not settings.google_client_secrets.exists():
                    raise FileNotFoundError(
                        f"OAuth client secret not found at {settings.google_client_secrets}. "
                        "Download a 'Desktop app' OAuth client from Google Cloud and save it there."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(settings.google_client_secrets), settings.gmail_scopes
                )
                # Starts a local server and opens (or prints) the consent URL.
                creds = flow.run_local_server(port=0)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json())

        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    @property
    def service(self):
        if self._service is None:
            self.authenticate()
        return self._service

    # -- Profile / labels ---------------------------------------------------
    def get_profile(self) -> tuple[str, str]:
        profile = self.service.users().getProfile(userId="me").execute()
        return profile["emailAddress"], str(profile["historyId"])

    def list_labels(self) -> dict[str, str]:
        resp = self.service.users().labels().list(userId="me").execute()
        return {lbl["id"]: lbl["name"] for lbl in resp.get("labels", [])}

    # -- Listing ------------------------------------------------------------
    def list_message_ids(
        self,
        *,
        label_ids: list[str] | None = None,
        query: str | None = None,
        max_results: int | None = None,
    ) -> Iterator[str]:
        yielded = 0
        page_token: str | None = None
        while True:
            resp = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=label_ids,
                    q=query,
                    pageToken=page_token,
                    maxResults=500,
                )
                .execute()
            )
            for msg in resp.get("messages", []):
                yield msg["id"]
                yielded += 1
                if max_results is not None and yielded >= max_results:
                    return
            page_token = resp.get("nextPageToken")
            if not page_token:
                return

    # -- Fetch + parse ------------------------------------------------------
    def get_message(self, message_id: str) -> EmailMessage:
        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        payload = raw.get("payload", {})
        headers = {
            h["name"].lower(): h["value"] for h in payload.get("headers", [])
        }
        label_ids = raw.get("labelIds", [])
        return EmailMessage(
            id=raw["id"],
            thread_id=raw.get("threadId", raw["id"]),
            from_addr=_first_addr(headers.get("from", "")),
            to_addrs=_all_addrs(headers.get("to", "")),
            cc_addrs=_all_addrs(headers.get("cc", "")),
            subject=headers.get("subject", ""),
            snippet=html.unescape(raw.get("snippet", "")),
            body_text=_extract_body(payload),
            ts=int(raw.get("internalDate", "0")) // 1000,  # ms -> s
            label_ids=label_ids,
            is_unread="UNREAD" in label_ids,
            size_estimate=int(raw.get("sizeEstimate", 0)),
        )

    # -- Incremental --------------------------------------------------------
    def list_history(self, start_history_id: str) -> HistoryChanges:
        added: list[str] = []
        deleted: list[str] = []
        new_history_id: str | None = None
        page_token: str | None = None
        try:
            while True:
                resp = (
                    self.service.users()
                    .history()
                    .list(
                        userId="me",
                        startHistoryId=start_history_id,
                        historyTypes=["messageAdded", "messageDeleted"],
                        pageToken=page_token,
                    )
                    .execute()
                )
                new_history_id = str(resp.get("historyId", new_history_id or start_history_id))
                for record in resp.get("history", []):
                    for item in record.get("messagesAdded", []):
                        added.append(item["message"]["id"])
                    for item in record.get("messagesDeleted", []):
                        deleted.append(item["message"]["id"])
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
        except HttpError as e:
            if e.resp.status == 404:
                # startHistoryId too old — caller should fall back to full backfill.
                return HistoryChanges([], [], None, history_too_old=True)
            raise
        return HistoryChanges(added, deleted, new_history_id)


# --- MIME parsing helpers ---------------------------------------------------
def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")


def _strip_html(raw_html: str) -> str:
    text = _TAG_RE.sub(" ", raw_html)
    text = html.unescape(text)
    return _WS_RE.sub("\n", text).strip()


def _extract_body(payload: dict) -> str:
    """Walk the MIME tree and return the best-effort plain text of a message body."""
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime == "text/plain" and body_data:
        return _decode(body_data)

    parts = payload.get("parts")
    if parts:
        # Prefer a text/plain part anywhere in the subtree.
        for part in parts:
            if part.get("mimeType") == "text/plain":
                text = _extract_body(part)
                if text:
                    return text
        # Otherwise recurse (handles multipart/alternative, multipart/mixed, ...).
        for part in parts:
            text = _extract_body(part)
            if text:
                return text

    if mime == "text/html" and body_data:
        return _strip_html(_decode(body_data))
    return ""


def _first_addr(header_value: str) -> str:
    addrs = _all_addrs(header_value)
    return addrs[0] if addrs else ""


def _all_addrs(header_value: str) -> list[str]:
    if not header_value:
        return []
    # getaddresses handles "Name <a@b.com>, other@c.com" robustly.
    return [addr for _name, addr in getaddresses([header_value]) if addr]
