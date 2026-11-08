"""Calendar events for an engagement: .ics download (CAL-3) and Google Calendar (CAL-1/2).

Exclusive contracts become one all-day multi-day event. Part-time contracts become
recurring all-day events that follow the schedule pattern; 4-on/4-off contracts use
one event per working run so the calendar never shows a day the contract doesn't work.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from .schedule import blocked_ranges, worked_days

WEEKLY = {"mon_fri": "MO,TU,WE,TH,FR", "nights": "MO,TU,WE,TH,FR", "weekends": "SA,SU"}


@dataclass
class EventSpec:
    start: date
    end_exclusive: date
    rrule: str | None = None


def event_specs(start: date, end: date, pattern: str, exclusive: bool) -> list[EventSpec]:
    if exclusive:
        return [EventSpec(start, end + timedelta(days=1))]
    if pattern in WEEKLY:
        days = worked_days(start, end, pattern)
        if not days:
            return []
        until = end.strftime("%Y%m%d")
        return [
            EventSpec(
                days[0],
                days[0] + timedelta(days=1),
                f"RRULE:FREQ=WEEKLY;BYDAY={WEEKLY[pattern]};UNTIL={until}",
            )
        ]
    return [
        EventSpec(s, e + timedelta(days=1))
        for s, e in blocked_ranges(start, end, pattern, exclusive)
    ]


def title(posting_title: str, company: str) -> str:
    return f"Shift: {posting_title} @ {company}"


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """RFC 5545 line folding at 75 octets."""
    raw = line.encode()
    if len(raw) <= 75:
        return line
    parts, chunk = [], b""
    for ch in line:
        b = ch.encode()
        if len(chunk) + len(b) > (75 if not parts else 74):
            parts.append(chunk.decode())
            chunk = b""
        chunk += b
    parts.append(chunk.decode())
    return "\r\n ".join(parts)


def ics(engagement_id: str, summary: str, location: str, description: str, specs) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Shift//Contract calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for i, s in enumerate(specs):
        lines += [
            "BEGIN:VEVENT",
            f"UID:{engagement_id}-{i}@shift.local",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{s.start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{s.end_exclusive.strftime('%Y%m%d')}",
            f"SUMMARY:{_escape(summary)}",
            f"LOCATION:{_escape(location)}",
            f"DESCRIPTION:{_escape(description)}",
            "TRANSP:OPAQUE",
        ]
        if s.rrule:
            lines.append(s.rrule)
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def google_body(summary: str, location: str, description: str, s: EventSpec) -> dict:
    body = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {"date": s.start.isoformat()},
        "end": {"date": s.end_exclusive.isoformat()},
        "transparency": "opaque",
    }
    if s.rrule:
        body["recurrence"] = [s.rrule]
    return body
