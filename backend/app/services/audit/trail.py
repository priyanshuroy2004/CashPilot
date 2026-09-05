"""
Audit Trail Service — Phase 4

Provides immutable event logging for all state changes in CashPilot AI.

RULES:
  - Events are NEVER deleted or updated.
  - created_at is set once and never modified.
  - All significant state changes (status, assignment, notes) must be logged.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import AuditTrailEvent


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def log_event(
    db: Session,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor: str = "system",
    from_value: Optional[Dict[str, Any]] = None,
    to_value: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
) -> AuditTrailEvent:
    """
    Persist an immutable audit trail event.

    Parameters
    ----------
    db          : Active SQLAlchemy session (caller must commit).
    entity_type : EXCEPTION_CASE | CASH_GAP_ALERT | FORECAST | SYSTEM
    entity_id   : case_id / alert_id / forecast_id / "SYSTEM"
    event_type  : DETECTION | STATUS_CHANGE | ASSIGNMENT | NOTE_ADDED |
                  ACKNOWLEDGEMENT | RESOLUTION | ESCALATION | ENGINE_RUN
    actor       : Who triggered the event ("system" or "user").
    from_value  : Previous state dict (e.g. {"status": "OPEN"}).
    to_value    : New state dict (e.g. {"status": "IN_REVIEW"}).
    notes       : Free-text notes.

    Returns
    -------
    AuditTrailEvent (not yet committed — caller must db.commit()).
    """
    event = AuditTrailEvent(
        event_id=f"AUD-{uuid.uuid4().hex[:16].upper()}",
        entity_type=entity_type.upper(),
        entity_id=str(entity_id),
        event_type=event_type.upper(),
        actor=actor,
        from_value=from_value,
        to_value=to_value,
        notes=notes,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    return event


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------

def get_events_for_entity(
    db: Session,
    entity_id: str,
    entity_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[AuditTrailEvent]:
    """Return audit events for a specific entity, newest first."""
    query = db.query(AuditTrailEvent).filter(
        AuditTrailEvent.entity_id == entity_id
    )
    if entity_type:
        query = query.filter(AuditTrailEvent.entity_type == entity_type.upper())
    return (
        query.order_by(AuditTrailEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_recent_events(
    db: Session,
    entity_type: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[AuditTrailEvent], int]:
    """Return paginated audit events, newest first."""
    query = db.query(AuditTrailEvent)
    if entity_type:
        query = query.filter(AuditTrailEvent.entity_type == entity_type.upper())
    if event_type:
        query = query.filter(AuditTrailEvent.event_type == event_type.upper())
    total = query.count()
    items = (
        query.order_by(AuditTrailEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total
