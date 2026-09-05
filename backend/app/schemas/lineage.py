"""
Pydantic Schemas for Money Lineage Graph API.
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class LineageNodeData(BaseModel):
    category: str
    title: str
    source_system: str
    record_id: str
    amount_paise: Optional[int] = None
    amount_inr: str
    date: Optional[str] = None
    status: str
    status_label: str
    visual_status: str  # green | yellow | red | grey | blue
    is_missing: bool = False
    confidence: Optional[float] = None
    rule: Optional[str] = None
    discrepancy: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    related_records: List[str] = Field(default_factory=list)


class LineageNodePosition(BaseModel):
    x: float
    y: float


class LineageNode(BaseModel):
    id: str
    type: str = "lineageNode"
    position: LineageNodePosition
    data: LineageNodeData


class LineageEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    animated: Optional[bool] = False
    style: Optional[Dict[str, Any]] = None


class LineageSummary(BaseModel):
    complete: bool
    total_nodes: int
    total_edges: int
    status: str  # RECONCILED | AT_RISK
    gross_amount_paise: Optional[int] = 0
    gross_amount_inr: str
    net_settled_inr: str
    break_point: Optional[str] = None


class RootEntity(BaseModel):
    type: str
    id: str


class LineageGraphResponse(BaseModel):
    root_entity: RootEntity
    summary: LineageSummary
    nodes: List[LineageNode]
    edges: List[LineageEdge]
