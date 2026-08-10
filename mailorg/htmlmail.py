"""Make an email's HTML safe to display.

Email HTML is untrusted input written by strangers, so it gets three independent
defences and this module is the first:

1. **Here** — nh3 (Rust "ammonia" bindings) parses the markup into a tree and rebuilds
   it from an allowlist. Regex-based stripping is not good enough: malformed markup
   defeats it routinely, which is why Phase 1's ``_strip_html`` needed four bug fixes.
2. A sandboxed ``<iframe>`` in the browser, which forbids script execution outright.
3. A CSP inside that frame, which forbids remote fetches.

**Remote images are neutralised by default.** A 1x1 image in marketing mail is a
tracking pixel: loading it tells the sender you opened the message, when, and roughly
where from. Gmail defuses this by proxying images through Google; we cannot do that
without sending Google our mail, so we simply do not load them until asked.

Because the render frame runs no JavaScript, "show images" cannot be a client-side
toggle — the caller re-requests the message with ``allow_remote=True`` instead.
"""

from __future__ import annotations

import re

import nh3

# Structural and formatting tags an email legitimately needs. Deliberately excludes
# script/iframe/object/embed/form/input — nothing here can execute or exfiltrate.
ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "center", "code", "col",
    "colgroup", "dd", "div", "dl", "dt", "em", "figure", "figcaption", "font", "h1",
    "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p", "pre", "s",
    "small", "span", "strike", "strong", "sub", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "tr", "u", "ul",
}

# Presentation attributes only. No event handlers (on*) survive the allowlist.
ALLOWED_ATTRS = {
    "*": {"style", "class", "align", "valign", "width", "height", "bgcolor", "dir", "title"},
    # No "rel" here: link_rel below sets it, and nh3 refuses to let both manage it.
    "a": {"href", "target"},
    "img": {"src", "alt", "width", "height", "border"},
    "table": {"cellpadding", "cellspacing", "border", "role"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "col": {"span"},
    "font": {"color", "face", "size"},
}

# Only these URL schemes may appear in href. Excludes javascript: and data:.
ALLOWED_SCHEMES = {"http", "https", "mailto", "tel"}

# CSS can fetch too (background-image:url(...)), which is a tracking vector that never
# passes through an <img> tag.
_CSS_URL_RE = re.compile(r"url\s*\(\s*['\"]?\s*(?:https?:|//)[^)]*\)", re.I)
# Matches the src of an <img> pointing anywhere off-machine.
_IMG_SRC_RE = re.compile(r"(<img\b[^>]*?\s)src\s*=\s*(\"[^\"]*\"|'[^']*')", re.I)
_REMOTE_RE = re.compile(r"^['\"]?\s*(?:https?:)?//", re.I)

# A transparent 1x1 GIF: keeps the layout box so tables do not collapse, loads nothing.
_BLANK_PIXEL = (
    "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


def _clean_style(value: str) -> str:
    """Drop remote fetches from an inline style, keeping the rest of the formatting."""
    return _CSS_URL_RE.sub("none", value)


def _attribute_filter(tag: str, attr: str, value: str) -> str | None:
    if attr == "style":
        return _clean_style(value)
    return value


def sanitize(html: str, *, allow_remote_images: bool = False) -> tuple[str, int]:
    """Return (safe_html, blocked_image_count).

    Args:
        html: the raw ``text/html`` part of the message.
        allow_remote_images: when False (default) every off-machine image is replaced
            with a transparent pixel and counted.
    """
    if not html or not html.strip():
        return "", 0

    cleaned = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        url_schemes=ALLOWED_SCHEMES,
        attribute_filter=_attribute_filter,
        # Every surviving link opens in a new tab and cannot reach window.opener.
        link_rel="noopener noreferrer nofollow",
    )

    if allow_remote_images:
        return cleaned, 0

    blocked = 0

    def swap(m: re.Match[str]) -> str:
        nonlocal blocked
        if not _REMOTE_RE.match(m.group(2)):
            return m.group(0)  # already inline (e.g. a data: URI) — harmless
        blocked += 1
        return f'{m.group(1)}src="{_BLANK_PIXEL}"'

    return _IMG_SRC_RE.sub(swap, cleaned), blocked


def has_content(html: str) -> bool:
    """True if the HTML carries anything worth rendering (not just an empty shell)."""
    if not html:
        return False
    return bool(nh3.clean(html, tags=set()).strip())
