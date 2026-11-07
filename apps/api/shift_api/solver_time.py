from datetime import timezone


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def overlap(a, b, c, d):
    return utc(a) < utc(d) and utc(c) < utc(b)
