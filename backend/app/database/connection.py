"""
Database connection and session management.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://cashpilot:cashpilot_dev_password@localhost:5432/cashpilot"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,         # verify connections before checkout
    pool_size=10,
    max_overflow=20,
    echo=False,                 # set True for SQL debug logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verify the database is reachable. Returns True if OK."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
