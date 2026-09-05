"""
Pydantic schemas for Phase 4 Audit Trail.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: int
    event_id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor: str
    from_value: Optional[Dict[str, Any]] = None
    to_value: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class PaginatedAuditEvents(BaseModel):
    total: int
    items: List[AuditEventResponse]
    limit: int
    offset: int
