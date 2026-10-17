"""Clock check for OSM time conditions (owner-approved improvement, 17 Oct 2026).

Reads the common UK forms inside `value @ (condition)`: weekday lists and ranges
(Mo-Fr, Sa,Su), times and time ranges (07:00-09:30, 16:00-18:30, 22:00-06:00 over
midnight), joined by ',' or ';', and "24/7". Anything else (public holidays, dates,
months, school terms, sunrise, vehicle or length conditions...) is not understood and
returns None, so the caller keeps the rule in force: never more permissive than before.
The time passed in is UK local time chosen by the caller; no time zone is guessed here.
"""
from __future__ import annotations

import re
from datetime import datetime

DAYS = ("mo", "tu", "we", "th", "fr", "sa", "su")
_TIME = r"(\d{1,2}):(\d{2})"
_RANGE = re.compile(rf"^{_TIME}\s*-\s*{_TIME}$")
_DAY_PART = re.compile(r"^(mo|tu|we|th|fr|sa|su)(?:\s*-\s*(mo|tu|we|th|fr|sa|su))?$")


def _days(text: str) -> set[int] | None:
    out: set[int] = set()
    for part in text.split(","):
        m = _DAY_PART.match(part.strip().lower())
        if not m:
            return None
        a = DAYS.index(m.group(1))
        b = DAYS.index(m.group(2)) if m.group(2) else a
        out.update(range(a, b + 1) if a <= b else [*range(a, 7), *range(0, b + 1)])
    return out


def _minutes(h: str, m: str) -> int | None:
    h_, m_ = int(h), int(m)
    return h_ * 60 + m_ if 0 <= h_ <= 24 and 0 <= m_ < 60 and h_ * 60 + m_ <= 1440 else None


def _rule_applies(rule: str, when: datetime) -> bool | None:
    """One rule such as 'Mo-Fr 07:00-09:30,16:00-18:30' or '07:00-19:00' or 'Sa'."""
    rule = rule.strip()
    if rule.lower() == "24/7":
        return True
    words = rule.split(None, 1)
    days = None
    times_text = rule
    if words and _days(words[0]) is not None:
        days = _days(words[0])
        times_text = words[1] if len(words) > 1 else ""
    day, now = when.weekday(), when.hour * 60 + when.minute
    if not times_text.strip():
        return None if days is None else day in days
    hit = False
    for part in times_text.split(","):
        m = _RANGE.match(part.strip())
        if not m:
            return None
        start, end = _minutes(m.group(1), m.group(2)), _minutes(m.group(3), m.group(4))
        if start is None or end is None:
            return None
        if start <= end:
            inside, on_day = start <= now < end, day
        else:  # over midnight: the part after midnight belongs to the previous day's rule
            inside = now >= start or now < end
            on_day = day if now >= start else (day - 1) % 7
        if inside and (days is None or on_day in days):
            hit = True
    return hit


def condition_applies(condition: str, when: datetime) -> bool | None:
    """True/False when the whole condition is understood, None when any part is not."""
    text = condition.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    if not text or " AND " in text.upper() or any(c in text for c in "<>="):
        return None
    results = [_rule_applies(r, when) for r in text.split(";") if r.strip()]
    if not results or any(r is None for r in results):
        return None
    return any(results)


def parts(value: str) -> list[tuple[str, str]]:
    """'no @ (Mo-Fr 07:00-10:00); destination @ (Sa)' -> [(value, condition), ...]."""
    out, depth, current = [], 0, ""
    for ch in value:  # split on ';' outside brackets only
        depth += ch == "("
        depth -= ch == ")"
        if ch == ";" and depth == 0:
            out.append(current)
            current = ""
        else:
            current += ch
    out.append(current)
    return [(p.split("@", 1)[0].strip().lower(), p.split("@", 1)[1].strip()) for p in out if "@" in p]
