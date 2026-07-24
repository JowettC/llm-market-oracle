"""Date-masking utility for the lookahead probe (PRD §7.3).

Strips explicit dates from text so a model cannot key on a remembered calendar
date to recall an outcome. If masking dates makes an LLM's directional skill
collapse, that skill was leaning on date recognition — a memorization tell.

Leaf module (no project imports) so both the prompts and the probe runner can
depend on it without cycles.
"""

from __future__ import annotations

import re

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)

# Order matters: match the most specific patterns first.
_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?Z?)?\b"),  # ISO date/time
    re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b", re.I),  # Mar 3, 2026
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\.?\s+\d{{4}}\b", re.I),  # 3 March 2026
    re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\b", re.I),  # March 3
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),  # 03/03/2026
    re.compile(r"\b(?:19|20)\d{2}\b"),  # bare year
]

_PLACEHOLDER = "[DATE]"


def mask_dates(text: str) -> str:
    """Replace date-like substrings with ``[DATE]``. Idempotent."""
    if not text:
        return text
    out = text
    for pat in _PATTERNS:
        out = pat.sub(_PLACEHOLDER, out)
    # collapse runs like "[DATE] [DATE]" that adjacent patterns can produce
    out = re.sub(r"(?:\[DATE\]\s*){2,}", "[DATE] ", out)
    return out.strip()
