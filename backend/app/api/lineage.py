"""
Money Lineage Graph REST API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.lineage import LineageGraphResponse
from app.services.lineage.builder import build_money_lineage_graph

router = APIRouter(prefix="/api/lineage", tags=["Lineage"])


@router.get("/{entity_type}/{entity_id}", response_model=LineageGraphResponse)
def get_money_lineage(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
):
    """
    Generate the interactive Money Lineage Graph for any financial entity:
    order | payment | settlement | bank | exception | refund
    """
    valid_types = {"order", "payment", "settlement", "bank", "bank_transaction", "exception", "refund"}
    if entity_type.lower() not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type '{entity_type}'. Must be one of {sorted(list(valid_types))}",
        )

    try:
        graph = build_money_lineage_graph(db, entity_type=entity_type, entity_id=entity_id)
        return graph
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate money lineage graph for {entity_type}/{entity_id}: {str(exc)}",
        )
