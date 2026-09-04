"""Best-effort extraction of a case's published/decision date from its page
text. WRC and Equality Tribunal (DEC-E) records carry an explicit labeled
field; Labour Court and Equality Tribunal (DEC-S) only state the date in a
signature block near the end of the text; EAT records vary. See
ARCHITECTURE.md for the real examples this was derived from.
"""

import re
from datetime import date, datetime

_MONTH_YEAR = r"\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
_NUMERIC = r"\d{1,2}/\d{1,2}/\d{4}"
_ANY_DATE = re.compile(f"({_MONTH_YEAR}|{_NUMERIC})", re.I)

_LABELED_PATTERNS = [
    re.compile(rf"Dated:\s*({_MONTH_YEAR}|{_NUMERIC})", re.I),
    re.compile(rf"Date of issue:\s*({_MONTH_YEAR}|{_NUMERIC})", re.I),
]

_LABOUR_COURT_SIGNOFF = re.compile(
    rf"Signed on behalf of the Labour Court.{{0,300}}?({_MONTH_YEAR}|{_NUMERIC})",
    re.I | re.S,
)


def _normalize(raw: str) -> str | None:
    raw = raw.strip()
    raw = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", raw, flags=re.I)
    for fmt in ("%d/%m/%Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract_published_date(text: str) -> str | None:
    for pattern in _LABELED_PATTERNS:
        match = pattern.search(text)
        if match:
            return _normalize(match.group(1)) or match.group(1).strip()

    match = _LABOUR_COURT_SIGNOFF.search(text)
    if match:
        return _normalize(match.group(1)) or match.group(1).strip()

    matches = _ANY_DATE.findall(text)
    if matches:
        raw = matches[-1]
        return _normalize(raw) or raw.strip()

    return None