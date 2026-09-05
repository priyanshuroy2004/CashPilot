# backend/app/services/audit/__init__.py
from .trail import log_event, get_events_for_entity, get_recent_events

__all__ = ["log_event", "get_events_for_entity", "get_recent_events"]
