"""
AI Layer REST API endpoints for CashPilot AI.

Adheres strictly to the core principle:
- Deterministic backend code verifies financial data
- AI explains and synthesizes structured evidence
- Humans approve irreversible actions
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ai import (
    CaseExplanationResponse,
    AssistantQueryRequest,
    AssistantQueryResponse,
    DailyExceptionSummaryResponse,
)
from app.services.ai.evidence_builder import (
    build_case_evidence_package,
    build_settlement_evidence_package,
)
from app.services.ai.client import ai_client
from app.services.ai.router import route_and_execute_query
from app.services.ai.summaries import generate_daily_executive_summary

router = APIRouter(prefix="/api/ai", tags=["Financial AI Intelligence"])


@router.get(
    "/cases/{case_id}/explanation",
    response_model=CaseExplanationResponse,
    summary="Get AI evidence-backed case explanation",
)
def get_case_explanation(case_id: str, db: Session = Depends(get_db)):
    """
    Generates an evidence-backed financial root-cause explanation for an exception case.
    Uses strictly verified database records and provides actionable advisory next steps.
    """
    evidence_pkg = build_case_evidence_package(db, case_id)
    if not evidence_pkg:
        raise HTTPException(
            status_code=404,
            detail=f"Case '{case_id}' not found or has no linked evidence records.",
        )

    try:
        return ai_client.generate_case_explanation(evidence_pkg)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate AI case explanation: {str(exc)}",
        )


@router.post(
    "/assistant/query",
    response_model=AssistantQueryResponse,
    summary="Ask CashPilot AI financial assistant",
)
def ask_assistant(payload: AssistantQueryRequest, db: Session = Depends(get_db)):
    """
    Answers finance inquiries with verified facts, citations, and risk-rated advisory actions.
    Supported query intents:
      - Settlement fee/variance breakdown
      - Settlements missing in bank
      - Captured payments missing fulfillment
      - Missing refund accounting entries
      - Current cash liquidity and arrival timing
      - Highest-risk unresolved exceptions
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query parameter cannot be empty.")

    try:
        return route_and_execute_query(db, payload.query)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Assistant query failed: {str(exc)}",
        )


@router.get(
    "/executive-summary",
    response_model=DailyExceptionSummaryResponse,
    summary="Get CFO Daily Financial Control Briefing",
)
def get_executive_summary(db: Session = Depends(get_db)):
    """
    Generates enterprise-wide financial briefing covering cash posture, top risks,
    reconciliation accuracy, and unresolved exceptions.
    """
    try:
        return generate_daily_executive_summary(db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate executive summary: {str(exc)}",
        )


@router.get(
    "/settlements/{settlement_id}/explanation",
    response_model=AssistantQueryResponse,
    summary="Explain settlement calculation and bank verification",
)
def get_settlement_explanation(settlement_id: str, db: Session = Depends(get_db)):
    """
    Provides full financial intelligence breakdown for a specific gateway settlement batch.
    """
    evidence_pkg = build_settlement_evidence_package(db, settlement_id)
    if not evidence_pkg:
        raise HTTPException(
            status_code=404,
            detail=f"Settlement '{settlement_id}' not found.",
        )

    try:
        return ai_client.answer_assistant_query(
            f"Explain calculation and status of settlement {settlement_id}",
            evidence_pkg,
            "SETTLEMENT_EXPLANATION",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to explain settlement: {str(exc)}",
        )
