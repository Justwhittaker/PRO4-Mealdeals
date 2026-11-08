"""Weekday names shared by settings and the Dublin beat schedule."""

from __future__ import annotations

WEEKDAY_NAMES: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def weekday_index(value: str | int) -> int:
    """Monday is 0, matching ``datetime.weekday``."""
    if isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit()):
        index = int(value)
    else:
        key = str(value).strip().lower()
        if key not in WEEKDAY_NAMES:
            raise ValueError(f"Unknown weekday {value!r}")
        return WEEKDAY_NAMES.index(key)
    if index < 0 or index > 6:
        raise ValueError(f"Weekday index {index} is outside 0..6")
    return index


def weekday_name(value: str | int) -> str:
    return WEEKDAY_NAMES[weekday_index(value)]
