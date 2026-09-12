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

# Render and other cloud databases often supply postgres:// which SQLAlchemy 1.4+ rejects
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Ensure SSL mode is requested for external cloud database URLs (e.g. Render external hostnames)
if DATABASE_URL and "render.com" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"


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
