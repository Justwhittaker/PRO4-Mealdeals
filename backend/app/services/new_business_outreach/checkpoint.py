"""Single-row checkpoint so a weekly run resumes where the last one stopped."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.outreach_state import NewBusinessOutreachState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_checkpoint(session: Session) -> tuple[int, int, str]:
    row = session.get(NewBusinessOutreachState, 1)
    if row is None:
        row = NewBusinessOutreachState(id=1, next_tile_index=0, cycle=1, pending_subtiles=None)
        session.add(row)
        session.commit()
    return int(row.next_tile_index or 0), int(row.cycle or 1), row.pending_subtiles or ""


def save_checkpoint(
    session: Session,
    *,
    next_tile_index: int,
    cycle: int,
    pending_subtiles: str | None = None,
) -> None:
    row = session.get(NewBusinessOutreachState, 1)
    if row is None:
        row = NewBusinessOutreachState(id=1)
        session.add(row)
    row.next_tile_index = max(int(next_tile_index), 0)
    row.cycle = max(int(cycle), 1)
    row.pending_subtiles = pending_subtiles or None
    row.updated_at = _utcnow()
    session.commit()
