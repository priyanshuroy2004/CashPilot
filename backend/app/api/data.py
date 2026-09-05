"""
/api/data/* router — CSV upload, validation, and database import.

Endpoints
---------
POST /api/data/upload
    Accept one or more CSV files (multipart/form-data).
    Detect type, normalize columns, validate rows.
    Return per-file validation reports and session IDs.

POST /api/data/imports/{session_id}/commit
    Commit valid rows from a previous upload session to the database.

GET  /api/data/imports
    List historical DataImport records (committed imports).

GET  /api/data/imports/{import_id}
    Get a specific DataImport record by its integer database ID.
"""
from __future__ import annotations

import io
import logging
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import DataImport
from app.schemas.upload import (
    ColumnMappingItem,
    CommitResponse,
    FileUploadResult,
    ImportListItem,
    ImportListResponse,
    UploadResponse,
    ValidationError as SchemaValidationError,
)
from app.services.data_ingestion import importer, sessions
from app.services.data_ingestion.validator import validate_csv
from app.services.schema_normalizer.detector import detect_type
from app.services.schema_normalizer.mapper import map_columns, mapping_confidence

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["data"])

# ---------------------------------------------------------------------------
# Constants / safety limits
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",  # generic binary — we'll verify via content
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_csv_safe(content: bytes, filename: str) -> pd.DataFrame:
    """Parse CSV bytes; raise HTTPException on unrecoverable parse errors."""
    try:
        df = pd.read_csv(io.BytesIO(content), dtype=str)
        return df
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse '{filename}' as CSV: {exc}",
        )


def _check_file_size(file_bytes: bytes, filename: str) -> None:
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File '{filename}' exceeds {MAX_FILE_SIZE_MB} MB limit.",
        )


def _build_mapping_items(
    raw_columns: List[str],
    mapping: dict,
    dataset_type: str,
) -> List[ColumnMappingItem]:
    """Build ColumnMappingItem list (mapped + unmapped columns)."""
    items: List[ColumnMappingItem] = []
    mapped_set = set(mapping.keys())

    for col in raw_columns:
        if col in mapping:
            # HIGH if exact canonical name, MEDIUM otherwise
            conf = "HIGH" if mapping[col] == col else "MEDIUM"
            items.append(ColumnMappingItem(
                original=col,
                normalized=mapping[col],
                confidence=conf,
            ))
        else:
            items.append(ColumnMappingItem(
                original=col,
                normalized=col,   # passthrough
                confidence="UNMAPPED",
            ))
    return items


# ---------------------------------------------------------------------------
# POST /api/data/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload and validate one or more CSV files",
)
async def upload_files(
    files: List[UploadFile] = File(...),
) -> UploadResponse:
    """
    Accept CSV files, auto-detect their dataset type, normalize column names,
    validate every row, and return a per-file validation report plus a
    *session_id* that can be used to commit valid rows to the database.

    No database writes happen at this stage.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files received.",
        )

    results: List[FileUploadResult] = []

    for upload in files:
        filename = upload.filename or "upload.csv"

        # Security: check extension
        if not filename.lower().endswith(".csv"):
            results.append(FileUploadResult(
                session_id="",
                filename=filename,
                dataset_type="unknown",
                detection_confidence="UNKNOWN",
                row_count=0,
                valid_count=0,
                error_count=0,
                column_mapping=[],
                errors=[SchemaValidationError(
                    row=0,
                    field="file",
                    message=f"Rejected: '{filename}' is not a .csv file.",
                )],
            ))
            continue

        # Read bytes
        content = await upload.read()
        try:
            _check_file_size(content, filename)
        except HTTPException as e:
            results.append(FileUploadResult(
                session_id="",
                filename=filename,
                dataset_type="unknown",
                detection_confidence="UNKNOWN",
                row_count=0,
                valid_count=0,
                error_count=0,
                column_mapping=[],
                errors=[SchemaValidationError(row=0, field="file", message=e.detail)],
            ))
            continue

        # Empty file check
        if len(content) == 0:
            results.append(FileUploadResult(
                session_id="",
                filename=filename,
                dataset_type="unknown",
                detection_confidence="UNKNOWN",
                row_count=0,
                valid_count=0,
                error_count=0,
                column_mapping=[],
                errors=[SchemaValidationError(row=0, field="file", message="File is empty.")],
            ))
            continue

        # Parse CSV
        try:
            df = _read_csv_safe(content, filename)
        except HTTPException as e:
            results.append(FileUploadResult(
                session_id="",
                filename=filename,
                dataset_type="unknown",
                detection_confidence="UNKNOWN",
                row_count=0,
                valid_count=0,
                error_count=0,
                column_mapping=[],
                errors=[SchemaValidationError(row=0, field="file", message=e.detail)],
            ))
            continue

        if df.empty or len(df.columns) == 0:
            results.append(FileUploadResult(
                session_id="",
                filename=filename,
                dataset_type="unknown",
                detection_confidence="UNKNOWN",
                row_count=0,
                valid_count=0,
                error_count=0,
                column_mapping=[],
                errors=[SchemaValidationError(
                    row=0, field="file",
                    message="CSV has no data rows or no columns.",
                )],
            ))
            continue

        raw_columns = list(df.columns)

        # ── Detect type ──────────────────────────────────────────────────────
        dataset_type, score, detection_confidence = detect_type(raw_columns, filename)

        if dataset_type == "unknown":
            results.append(FileUploadResult(
                session_id="",
                filename=filename,
                dataset_type="unknown",
                detection_confidence="UNKNOWN",
                row_count=len(df),
                valid_count=0,
                error_count=len(df),
                column_mapping=_build_mapping_items(raw_columns, {}, ""),
                errors=[SchemaValidationError(
                    row=0,
                    field="columns",
                    message=(
                        "Could not determine dataset type from column names. "
                        f"Columns found: {', '.join(raw_columns[:10])}."
                    ),
                )],
            ))
            continue

        # ── Map columns ──────────────────────────────────────────────────────
        column_mapping, unmapped = map_columns(raw_columns, dataset_type)

        # ── Validate rows ────────────────────────────────────────────────────
        val_result = validate_csv(df, dataset_type, column_mapping)

        # ── Store session ────────────────────────────────────────────────────
        session_id = sessions.new_session_id()
        sessions.put({
            "session_id":           session_id,
            "filename":             filename,
            "dataset_type":         dataset_type,
            "detection_confidence": detection_confidence,
            "row_count":            val_result.row_count,
            "valid_count":          val_result.valid_count,
            "error_count":          val_result.error_count,
            "column_mapping":       [
                {"original": k, "normalized": v} for k, v in column_mapping.items()
            ],
            "errors":               [
                {"row": e.row, "field": e.field, "message": e.message}
                for e in val_result.errors
            ],
            "valid_rows":           val_result.valid_rows,
        })

        # ── Build response ───────────────────────────────────────────────────
        results.append(FileUploadResult(
            session_id=session_id,
            filename=filename,
            dataset_type=dataset_type,
            detection_confidence=detection_confidence,
            row_count=val_result.row_count,
            valid_count=val_result.valid_count,
            error_count=val_result.error_count,
            column_mapping=_build_mapping_items(raw_columns, column_mapping, dataset_type),
            errors=[
                SchemaValidationError(row=e.row, field=e.field, message=e.message)
                for e in val_result.errors
            ],
        ))

    return UploadResponse(files=results)


# ---------------------------------------------------------------------------
# POST /api/data/imports/{session_id}/commit
# ---------------------------------------------------------------------------
@router.post(
    "/imports/{session_id}/commit",
    response_model=CommitResponse,
    summary="Commit validated rows to the database",
)
def commit_import(
    session_id: str,
    db: Session = Depends(get_db),
) -> CommitResponse:
    """
    Commit valid rows from a previous upload session to PostgreSQL.
    Invalid rows are silently excluded.
    Duplicate primary keys are skipped automatically.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session '{session_id}' not found or expired.",
        )

    if session.get("committed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session '{session_id}' has already been committed.",
        )

    if session["valid_count"] == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid rows to import. Fix validation errors first.",
        )

    result = importer.commit_rows(
        db=db,
        dataset_type=session["dataset_type"],
        valid_rows=session["valid_rows"],
        filename=session["filename"],
    )
    sessions.mark_committed(session_id)

    return CommitResponse(
        session_id=session_id,
        dataset_type=result.dataset_type,
        imported=result.imported,
        skipped=result.skipped,
        data_import_id=result.data_import_id,
        message=result.message,
    )


# ---------------------------------------------------------------------------
# GET /api/data/imports
# ---------------------------------------------------------------------------
@router.get(
    "/imports",
    response_model=ImportListResponse,
    summary="List all data import records",
)
def list_imports(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> ImportListResponse:
    """Return historical DataImport audit records, newest first."""
    total = db.query(DataImport).count()
    records = (
        db.query(DataImport)
        .order_by(DataImport.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ImportListResponse(
        imports=[
            ImportListItem(
                id=r.id,
                filename=r.filename,
                dataset_type=r.dataset_type,
                row_count=r.row_count,
                status=r.status,
                error_count=r.error_count or 0,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in records
        ],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /api/data/imports/{import_id}
# ---------------------------------------------------------------------------
@router.get(
    "/imports/{import_id}",
    response_model=ImportListItem,
    summary="Get a specific import record",
)
def get_import(
    import_id: int,
    db: Session = Depends(get_db),
) -> ImportListItem:
    record = db.query(DataImport).filter(DataImport.id == import_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import record {import_id} not found.",
        )
    return ImportListItem(
        id=record.id,
        filename=record.filename,
        dataset_type=record.dataset_type,
        row_count=record.row_count,
        status=record.status,
        error_count=record.error_count or 0,
        created_at=record.created_at.isoformat() if record.created_at else "",
    )
