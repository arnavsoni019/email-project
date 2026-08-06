"""Make extracted email text readable for a human (and useful to a model).

Phase 1 extracts text *faithfully* — which for marketing mail means ~54% of the body is
raw click-tracking URLs. That wrecks the reading pane and, worse, fills the model's
limited input window with noise instead of content.

This module is applied at READ time, not sync time: ``messages.body_text`` keeps the
faithful extraction, so cleaning rules can change without re-syncing and a future
"show original" toggle still has something to show.

Used by:
  * ``pipelines.common.format_email_for_llm`` — so the model sees content, not URLs
  * ``web.api.get_message`` — so the reader shows the cleaned version
"""

from __future__ import annotations

import re

# A URL, stopping before trailing punctuation that is usually sentence-level.
_URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+")

# Whole lines that are navigational chrome rather than content.
_BOILERPLATE_RE = re.compile(
    r"^[ \t]*(?:"
    r"read (?:this article |more )?on linkedin.*"
    r"|view (?:this )?(?:email )?in (?:your )?browser.*"
    r"|(?:click here to )?unsubscribe.*"
    r"|manage (?:your )?(?:email )?(?:preferences|alerts|subscriptions?).*"
    r"|update your (?:email )?preferences.*"
    r"|you (?:are|'re) receiving this (?:email|message).*"
    r"|this (?:email|message) was sent (?:to|by).*"
    r"|(?:©|\(c\))\s?\d{4}.*"
    r"|all rights reserved.*"
    r"|privacy (?:notice|policy|statement).*"
    r"|terms of (?:use|service).*"
    r"|add (?:us|this email) to your (?:address book|safe senders).*"
    r"|if you (?:no longer wish|do not wish|would rather not).*"
    r"|sent from my (?:iphone|ipad|android|samsung).*"
    r")[ \t]*$",
    re.I | re.M,
)

# Rules of dashes/underscores/equals used as visual dividers.
_DIVIDER_RE = re.compile(r"^[ \t]*[-=_*~·—]{4,}[ \t]*$", re.M)
# A run of link placeholders left after substitution, e.g. "[a] [b] [c]".
_LINK_RUN_RE = re.compile(r"(?:\[[^\]\n]{1,60}\][ \t]*){2,}")
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")
_BLANKS_RE = re.compile(r"\n{3,}")
# Zero-width and other invisible characters some senders use for tracking/spacing.
_INVISIBLE_RE = re.compile(r"[​-‏  ﻿­]")


def _label_for(url: str) -> str:
    """Turn a tracking URL into a compact, still-informative label."""
    m = re.match(r"https?://(?:www\.)?([^/?#]+)", url)
    if not m:
        return "[link]"
    host = m.group(1)
    # Trim tracking subdomains so "t2.service.icicisecurities.com" reads usefully.
    parts = host.split(".")
    if len(parts) > 2 and len(parts[-2]) > 3:
        host = ".".join(parts[-2:])
    return f"[{host}]"


def clean_body(text: str, *, keep_links: bool = True) -> str:
    """Return a human-readable version of an extracted email body.

    Args:
        text: the faithfully-extracted body (``messages.body_text``).
        keep_links: replace URLs with a short ``[domain]`` label. When False, drop them.
    """
    if not text:
        return ""

    out = _INVISIBLE_RE.sub("", text)
    out = _URL_RE.sub((lambda m: _label_for(m.group(0))) if keep_links else "", out)
    out = _BOILERPLATE_RE.sub("", out)
    out = _DIVIDER_RE.sub("", out)
    # Collapse "[x] [x] [x]" runs down to a single label.
    out = _LINK_RUN_RE.sub(lambda m: m.group(0).split("]")[0] + "] ", out)
    out = _MULTISPACE_RE.sub(" ", out)
    out = "\n".join(line.rstrip() for line in out.split("\n"))
    out = _BLANKS_RE.sub("\n\n", out)
    return out.strip()
