"""Which days a contract occupies, and overlap checks (FLOW-3, FLOW-4, FEED-1).

Exclusive contracts block the whole date range. Non-exclusive contracts block only the
days their schedule pattern works, merged into consecutive runs.
"""

from datetime import date, timedelta

Range = tuple[date, date]  # inclusive


def worked_days(start: date, end: date, pattern: str) -> list[date]:
    days = []
    d = start
    while d <= end:
        offset = (d - start).days
        if pattern in {"mon_fri", "nights"}:
            on = d.weekday() < 5
        elif pattern == "weekends":
            on = d.weekday() >= 5
        elif pattern == "four_on_four_off":
            on = offset % 8 < 4
        else:
            on = True
        if on:
            days.append(d)
        d += timedelta(days=1)
    return days


def merge(days: list[date]) -> list[Range]:
    ranges: list[Range] = []
    for d in sorted(days):
        if ranges and d - ranges[-1][1] == timedelta(days=1):
            ranges[-1] = (ranges[-1][0], d)
        else:
            ranges.append((d, d))
    return ranges


def blocked_ranges(start: date, end: date, pattern: str, exclusive: bool) -> list[Range]:
    if exclusive:
        return [(start, end)]
    return merge(worked_days(start, end, pattern))


def overlap(a: list[Range], b: list[Range]) -> Range | None:
    """First overlapping span between two sets of inclusive ranges, if any."""
    for a0, a1 in a:
        for b0, b1 in b:
            lo, hi = max(a0, b0), min(a1, b1)
            if lo <= hi:
                return (lo, hi)
    return None
