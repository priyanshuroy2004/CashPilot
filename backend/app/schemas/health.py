"""Pydantic schemas for the health check endpoint."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "1.0.0"
