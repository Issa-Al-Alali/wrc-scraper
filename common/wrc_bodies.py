"""Maps WRC case records to the issuing "Body" (tribunal type).

The live site has no server-side filter for Body — the case listing pages
(`/en/cases/{year}/{month}/`) mix every tribunal's decisions together, so the
spider classifies each record before deciding whether it matches the
`-a body=...` argument it was invoked with.

Classification is prefix-based. Workplace Relations Commission, Equality
Tribunal and Employment Appeals Tribunal each use a small, closed set of
identifier prefixes (EAT in particular stopped issuing new decisions in
2015, so its prefix set cannot grow). Labour Court prefixes are open-ended
(legacy `LCR`/`AD`/`EDA`/`DIC` plus newer subject-specific appeal codes like
`DWT`, `FTD`, `HSD`, `PTD`, `UDD`), so it is the default classification for
any identifier that doesn't match one of the other three closed sets, rather
than an exhaustive whitelist. `body_from_content` is a cheap secondary check
used to log a warning if a record's page content disagrees with its
prefix-derived classification — see ARCHITECTURE.md.
"""

import re

WRC = "Workplace Relations Commission"
LABOUR_COURT = "Labour Court"
EQUALITY_TRIBUNAL = "Equality Tribunal"
EAT = "Employment Appeals Tribunal"

WRC_PREFIXES = ("ADJ", "IR-SC", "IR")
EQUALITY_TRIBUNAL_PREFIXES = ("DEC-E", "DEC-S")
EAT_PREFIXES = ("UD", "MN", "RP", "WT", "PW", "TE", "TU", "I", "P")

_WRC_SORTED = sorted(WRC_PREFIXES, key=len, reverse=True)
_EQUALITY_SORTED = sorted(EQUALITY_TRIBUNAL_PREFIXES, key=len, reverse=True)
_EAT_SORTED = sorted(EAT_PREFIXES, key=len, reverse=True)


def body_for_identifier(identifier: str) -> str:
    upper = identifier.upper()
    if any(upper.startswith(p) for p in _WRC_SORTED):
        return WRC
    if any(upper.startswith(p) for p in _EQUALITY_SORTED):
        return EQUALITY_TRIBUNAL
    if any(upper.startswith(p) for p in _EAT_SORTED):
        return EAT
    return LABOUR_COURT


_CONTENT_SIGNATURES = (
    (re.compile(r"adjudication officer decision", re.I), WRC),
    (re.compile(r"equality tribunal|equal status acts", re.I), EQUALITY_TRIBUNAL),
    (re.compile(r"employment appeals tribunal", re.I), EAT),
    (re.compile(r"signed on behalf of the labour court", re.I), LABOUR_COURT),
)


def body_from_content(text: str) -> str | None:
    for pattern, body in _CONTENT_SIGNATURES:
        if pattern.search(text):
            return body
    return None