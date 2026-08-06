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

# <style>/<script>/<head> must be dropped WITH their contents — stripping only the tags
# leaves raw CSS/JS in the body text, which then pollutes the UI and the LLM prompt.
_DROP_BLOCK_RE = re.compile(r"<(style|script|head|noscript)\b[^>]*>.*?</\1\s*>", re.S | re.I)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
# Structural tags that should become line breaks so paragraphs survive.
_BREAK_RE = re.compile(r"<br\s*/?>|</(p|div|tr|li|h[1-6]|table|blockquote)\s*>", re.I)
# Tolerates ">" inside quoted attribute values, e.g. <a data-x="a>b" style="...">.
# A plain <[^>]+> stops at the inner ">" and leaves half the tag as visible text.
_TAG_RE = re.compile(r"""<[a-zA-Z/!?][^>"']*(?:(?:"[^"]*"|'[^']*')[^>"']*)*>""", re.S)
# Fallback for malformed tags with an unbalanced quote, which defeat the pattern above.
# Bounded length so it can never swallow a large span of real text.
_TAG_SIMPLE_RE = re.compile(r"<[a-zA-Z/!?][^<>]{0,2000}?>", re.S)
_WS_RE = re.compile(r"[ \t]*\n[ \t\n]*")
_BLANKS_RE = re.compile(r"\n{3,}")

# Final safety net. Real emails are messy: senders leave bare CSS in their *plain-text*
# alternative, and attribute values containing ">" defeat a simple tag regex. These
# patterns clean up whatever survives, whichever route the text arrived by.
_AT_RULE_RE = re.compile(
    r"@(media|import|font-face|charset|supports)\b[^{;]*(\{[^{}]*(\{[^{}]*\}[^{}]*)*\}|;)",
    re.S | re.I,
)
# A CSS selector token: tag/class/id, optional pseudo, attribute or combinator.
# Deliberately strict — prose must never match, or real sentences get eaten.
_SEL = r"[.#]?[A-Za-z][\w\-]*(?:\[[^\]]{0,60}\])?(?:::?[\w\-()]+)?"
# A CSS rule: selectors, then a brace block that is clearly CSS — it must contain a
# colon AND a stronger signal (a semicolon, !important, or a hyphenated property).
# Without that second test, prose like "config {timeout: 30}" would be stripped.
_CSS_BODY = r"\{(?=[^{}]*:)[^{}]*(?:;|!important|[a-z]+-[a-z]+\s*:)[^{}]*\}"
_CSS_RULE_RE = re.compile(
    rf"{_SEL}(?:\s*[,>+~]\s*{_SEL})*\s*{_CSS_BODY}", re.S
)
# An unterminated tag running to end of input (truncated bodies).
_TAG_FRAG_RE = re.compile(r"<[a-zA-Z/][^<>]{0,400}$", re.S)


def _scrub_css(text: str) -> str:
    """Remove CSS rule blocks and stray tag fragments from already-extracted text."""
    text = _AT_RULE_RE.sub(" ", text)
    prev = None
    while prev != text:  # nested/consecutive rule blocks
        prev = text
        text = _CSS_RULE_RE.sub(" ", text)
    text = _TAG_FRAG_RE.sub(" ", text)
    return text


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
            from_name=_first_name(headers.get("from", "")),
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
    """Best-effort plain text from an HTML email body.

    Order matters: drop comments and style/script blocks (with their contents) first,
    then turn structural tags into line breaks, then remove what's left. Doing this the
    other way round leaves stylesheet text in the output.
    """
    text = _COMMENT_RE.sub(" ", raw_html)
    text = _DROP_BLOCK_RE.sub(" ", text)
    text = _BREAK_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = _TAG_SIMPLE_RE.sub(" ", text)  # malformed tags the quote-aware pass missed
    text = _scrub_css(text)  # catch what malformed markup let through
    text = html.unescape(text)
    text = text.replace(" ", " ").replace("‌", "")  # nbsp, zero-width non-joiner
    text = _WS_RE.sub("\n", text)
    text = _BLANKS_RE.sub("\n\n", text)
    return text.strip()


# Any common tag — senders embed inline markup (<a>, <span style=...>) in text/plain
# parts without a surrounding <html>, so looking only for document-level tags misses them.
_HTML_HINT_RE = re.compile(
    r"</?(?:html|body|head|style|script|div|span|table|tbody|tr|td|p|br|img|a|strong|b|em|font|ul|li|h[1-6])\b[^>]*>",
    re.I,
)


def _looks_like_html(text: str) -> bool:
    """True when text declared as plain actually carries HTML markup.

    Requires two or more tags so an isolated "<3" or a stray angle bracket in prose
    does not trigger stripping.
    """
    sample = text[:20000]
    hits = 0
    for _ in _HTML_HINT_RE.finditer(sample):
        hits += 1
        if hits >= 2:
            return True
    return False


def _extract_body(payload: dict) -> str:
    """Walk the MIME tree and return the best-effort plain text of a message body."""
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime == "text/plain" and body_data:
        text = _decode(body_data)
        # Trust the content over the declared type.
        if _looks_like_html(text):
            return _strip_html(text)
        return _BLANKS_RE.sub("\n\n", _scrub_css(text)).strip()

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


def _first_name(header_value: str) -> str:
    """Display name from a From header ("ICICI Direct" <x@y.com> -> "ICICI Direct").

    Falls back to the address' local part when no display name is present, so the UI
    always has something human-readable to show.
    """
    if not header_value:
        return ""
    parsed = getaddresses([header_value])
    if not parsed:
        return ""
    name, addr = parsed[0]
    name = name.strip().strip('"')
    if name:
        return name
    return addr.split("@")[0] if addr else ""


def _all_addrs(header_value: str) -> list[str]:
    if not header_value:
        return []
    # getaddresses handles "Name <a@b.com>, other@c.com" robustly.
    return [addr for _name, addr in getaddresses([header_value]) if addr]
