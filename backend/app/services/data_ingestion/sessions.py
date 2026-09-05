"""
Upload session store — in-memory keyed by UUID.

Each session represents a single uploaded file that has been validated
but not yet committed to the database.  Sessions expire after MAX_AGE_SECONDS.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

MAX_AGE_SECONDS = 3600  # sessions older than 1 hour are pruned

# ---------------------------------------------------------------------------
# Session shape (type hint only — plain dicts stored at runtime)
# ---------------------------------------------------------------------------
# {
#   "session_id": str,
#   "filename": str,
#   "dataset_type": str,
#   "detection_confidence": str,
#   "row_count": int,
#   "valid_count": int,
#   "error_count": int,
#   "column_mapping": list[dict],   # [{"original", "normalized"}]
#   "errors": list[dict],           # [{"row", "field", "message"}]
#   "valid_rows": list[dict],       # ready to insert
#   "committed": bool,
#   "created_at": float,            # time.time()
# }

_store: Dict[str, Dict[str, Any]] = {}


def new_session_id() -> str:
    return str(uuid.uuid4())


def put(session: Dict[str, Any]) -> None:
    _prune()
    session.setdefault("created_at", time.time())
    session.setdefault("committed", False)
    _store[session["session_id"]] = session


def get(session_id: str) -> Optional[Dict[str, Any]]:
    _prune()
    return _store.get(session_id)


def mark_committed(session_id: str) -> None:
    if session_id in _store:
        _store[session_id]["committed"] = True


def _prune() -> None:
    cutoff = time.time() - MAX_AGE_SECONDS
    stale = [k for k, v in _store.items() if v.get("created_at", 0) < cutoff]
    for k in stale:
        del _store[k]


def all_sessions() -> List[Dict[str, Any]]:
    _prune()
    return list(_store.values())
