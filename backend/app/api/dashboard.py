"""
Dashboard REST API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardOverviewResponse
from app.services.dashboard import get_dashboard_overview_metrics

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    Get live financial metrics and reconciliation summary for the Overview Dashboard.
    All data is computed on the fly from PostgreSQL — no hardcoding.
    """
    try:
        return get_dashboard_overview_metrics(db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard metrics: {str(exc)}",
        )
