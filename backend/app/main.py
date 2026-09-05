"""
CASHpilot AI — FastAPI Application Entry Point
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.api import health as health_router
from app.api import demo as demo_router
from app.api import data as data_router
from app.api import reconciliation as reconciliation_router
from app.api import dashboard as dashboard_router
from app.api import exceptions as exceptions_router
from app.api import financial as financial_router
from app.api import lineage as lineage_router
from app.api import ai as ai_router
from app.api import forecast as forecast_router
from app.api import audit as audit_router
from app.api import evaluation as evaluation_router
from app.database import engine
from app.models.models import Base


# ---------------------------------------------------------------------------
# Lifespan: create tables on startup (idempotent)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup if they don't exist."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        # Log but don't crash — health endpoint will report DB as unreachable
        import logging
        logging.getLogger(__name__).warning(f"DB startup create_all failed: {exc}")
    yield
    # shutdown: nothing to clean up


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CASHpilot AI — Backend API",
    description=(
        "Backend for CASHpilot AI: Finance Dashboard + Reconciliation Engine + Exceptions Workspace."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server, Vercel deployments, and configured frontend
# ---------------------------------------------------------------------------
raw_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
frontend_url = os.getenv("FRONTEND_URL", "")
if frontend_url:
    for url in frontend_url.split(","):
        clean = url.strip()
        if clean and clean not in raw_origins:
            raw_origins.append(clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=raw_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health_router.router)
app.include_router(demo_router.router)
app.include_router(data_router.router)
app.include_router(reconciliation_router.router)
app.include_router(dashboard_router.router)
app.include_router(exceptions_router.router)
app.include_router(financial_router.router)
app.include_router(lineage_router.router)
app.include_router(ai_router.router)
app.include_router(forecast_router.router)
app.include_router(audit_router.router)
app.include_router(evaluation_router.router)


@app.get("/", include_in_schema=False)
def root():
    return {
        "app": "CASHpilot AI",
        "version": "4.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }

