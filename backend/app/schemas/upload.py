"""
Pydantic schemas for the /api/data/* upload endpoints.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class ColumnMappingItem(BaseModel):
    original: str
    normalized: str
    confidence: str  # HIGH | MEDIUM | UNMAPPED


class ValidationError(BaseModel):
    row: int
    field: str
    message: str


class FileUploadResult(BaseModel):
    session_id: str
    filename: str
    dataset_type: str          # orders | payments | ... | unknown
    detection_confidence: str  # HIGH | MEDIUM | LOW | UNKNOWN
    row_count: int
    valid_count: int
    error_count: int
    column_mapping: List[ColumnMappingItem]
    errors: List[ValidationError]


class UploadResponse(BaseModel):
    files: List[FileUploadResult]


class CommitResponse(BaseModel):
    session_id: str
    dataset_type: str
    imported: int
    skipped: int
    data_import_id: int
    message: str


class ImportListItem(BaseModel):
    id: int
    filename: str
    dataset_type: str
    row_count: Optional[int]
    status: str
    error_count: int
    created_at: str


class ImportListResponse(BaseModel):
    imports: List[ImportListItem]
    total: int
