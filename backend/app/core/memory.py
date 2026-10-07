"""Return freed heap pages to the OS after large request allocations."""

from __future__ import annotations

import ctypes
import gc


def release_heap_to_os() -> None:
    """Drop unreferenced objects and ask glibc to return free arenas.

    CPython keeps malloc arenas after a large response, so RSS stays at the
    high-water mark on a long-lived uvicorn process. No-op if malloc_trim
    is unavailable.
    """
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        return
