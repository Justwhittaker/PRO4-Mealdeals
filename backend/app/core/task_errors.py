"""Errors that must abort a scrape task instead of being isolated per city."""

from __future__ import annotations

# Celery raises these inside the task. Catching them as a city/source failure
# would let a zone ignore its time limit and run until the hard kill.
_FATAL_TASK_ERROR_NAMES = frozenset(
    {
        "SoftTimeLimitExceeded",
        "TimeLimitExceeded",
    }
)


def is_fatal_task_error(exc: BaseException) -> bool:
    return exc.__class__.__name__ in _FATAL_TASK_ERROR_NAMES


def reraise_if_fatal(exc: BaseException) -> None:
    """Re-raise Celery time limits swallowed by a broad ``except Exception``."""
    if is_fatal_task_error(exc):
        raise exc
