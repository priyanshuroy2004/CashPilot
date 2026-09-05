"""
Audit Trail API — Phase 4

Provides read-only access to the immutable audit event log.

Endpoints:
  GET /api/audit/events               — paginated events, filterable
  GET /api/audit/events/{entity_id}   — events for a specific entity
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.audit import AuditEventResponse, PaginatedAuditEvents
from app.services.audit.trail import get_recent_events, get_events_for_entity

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])


def _fmt_dt(dt) -> str:
    return dt.isoformat() if dt else ""


def _serialize(event) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        event_id=event.event_id,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        event_type=event.event_type,
        actor=event.actor,
        from_value=event.from_value,
        to_value=event.to_value,
        notes=event.notes,
        created_at=_fmt_dt(event.created_at),
    )


@router.get("/events", response_model=PaginatedAuditEvents, summary="Paginated audit trail events")
def list_audit_events(
    entity_type: Optional[str] = Query(None, description="EXCEPTION_CASE | CASH_GAP_ALERT | FORECAST | SYSTEM"),
    event_type: Optional[str] = Query(None, description="DETECTION | STATUS_CHANGE | ASSIGNMENT | NOTE_ADDED | ENGINE_RUN | ..."),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Returns paginated audit trail events, newest first.
    Filter by entity_type or event_type.
    """
    items, total = get_recent_events(
        db=db,
        entity_type=entity_type,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    return PaginatedAuditEvents(
        total=total,
        items=[_serialize(e) for e in items],
        limit=limit,
        offset=offset,
    )


@router.get("/events/{entity_id}", response_model=PaginatedAuditEvents, summary="Audit trail for a specific entity")
def get_entity_audit_trail(
    entity_id: str,
    entity_type: Optional[str] = Query(None, description="EXCEPTION_CASE | CASH_GAP_ALERT | FORECAST | SYSTEM"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Returns the complete audit trail for a specific entity (case_id, alert_id, etc.).
    Events are immutable and ordered newest first.
    """
    items = get_events_for_entity(
        db=db,
        entity_id=entity_id,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
    return PaginatedAuditEvents(
        total=len(items),
        items=[_serialize(e) for e in items],
        limit=limit,
        offset=offset,
    )
