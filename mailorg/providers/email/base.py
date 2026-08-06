"""The email provider abstraction.

``sync.py`` and everything above it depend only on this interface, never on Gmail
directly. To add Outlook later you implement one new ``EmailProvider`` subclass and
change nothing else.

Timestamps are unix-epoch *seconds*. Address fields are already parsed to plain email
strings (display names stripped) so downstream code never re-parses MIME headers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass
class EmailMessage:
    """A single message, normalised into the shape mailorg stores.

    LLM-derived fields (category/tldr/priority) are intentionally *not* here — the
    provider only knows raw mail; enrichment happens later in the pipelines.
    """

    id: str                      # provider message id (Gmail message id)
    thread_id: str               # provider thread/conversation id
    from_addr: str               # sender email, e.g. "alice@example.com"
    from_name: str               # sender display name, e.g. "ICICI Direct" (may be "")
    to_addrs: list[str]          # recipient emails
    cc_addrs: list[str]          # cc'd emails
    subject: str
    snippet: str                 # short preview supplied by the provider
    body_text: str               # best-effort plain-text body
    ts: int                      # unix epoch SECONDS (provider receipt time)
    label_ids: list[str] = field(default_factory=list)
    is_unread: bool = False
    size_estimate: int = 0       # approximate size in bytes


@dataclass
class HistoryChanges:
    """The delta since a given history point, for incremental sync.

    ``history_too_old`` signals the stored history id has expired (provider no longer
    has that far back), telling the caller to fall back to a full backfill.
    """

    added_message_ids: list[str]
    deleted_message_ids: list[str]
    new_history_id: str | None
    history_too_old: bool = False


class EmailProvider(ABC):
    """Read-only email access (Phase 1). Write methods arrive in Phase 5."""

    @abstractmethod
    def authenticate(self) -> None:
        """Ensure valid credentials exist (interactive login on first run)."""

    @abstractmethod
    def get_profile(self) -> tuple[str, str]:
        """Return ``(email_address, current_history_id)`` for the account."""

    @abstractmethod
    def list_message_ids(
        self,
        *,
        label_ids: list[str] | None = None,
        query: str | None = None,
        max_results: int | None = None,
    ) -> Iterator[str]:
        """Yield message ids matching the filter, handling pagination internally."""

    @abstractmethod
    def get_message(self, message_id: str) -> EmailMessage:
        """Fetch and parse a single message into an :class:`EmailMessage`."""

    @abstractmethod
    def list_history(self, start_history_id: str) -> HistoryChanges:
        """Return message changes since ``start_history_id`` (incremental sync)."""

    @abstractmethod
    def list_labels(self) -> dict[str, str]:
        """Return a mapping of ``label_id -> human-readable label name``."""
