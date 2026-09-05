"""
Phase 4 Integration Tests — Forecast, Cash-Gap Alerts, Audit Trail, Evaluation

These tests verify that all Phase 4 components work correctly on top of the
existing Phase 1–3 infrastructure.

Run with:
  cd backend && python -m pytest tests/test_phase4.py -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.models import Base
from app.database import get_db

# ── In-memory SQLite test database ─────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite:///./test_phase4.db"

engine_test = create_engine(
    SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    import os
    if os.path.exists("test_phase4.db"):
        os.remove("test_phase4.db")


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_db_session():
    return TestSessionLocal()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Forecast Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestForecastEngine:
    def test_run_forecast_returns_200(self):
        """POST /api/forecast/run returns 200 even with empty DB."""
        r = client.post("/api/forecast/run")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "message" in data
        assert "unsettled_payments_count" in data
        assert "forecasts_created" in data
        assert "horizon_summary" in data

    def test_run_forecast_has_all_horizons(self):
        r = client.post("/api/forecast/run")
        assert r.status_code == 200
        hs = r.json()["horizon_summary"]
        for horizon in ["1", "3", "7", "14"]:
            assert horizon in hs, f"Missing horizon {horizon} in summary"
            assert "payment_count" in hs[horizon]
            assert "expected_amount_paise" in hs[horizon]
            assert "expected_amount_inr" in hs[horizon]

    def test_run_forecast_gap_detection_included(self):
        r = client.post("/api/forecast/run")
        data = r.json()
        assert "gap_detection" in data

    def test_forecast_summary_returns_200(self):
        r = client.get("/api/forecast/summary")
        assert r.status_code == 200
        data = r.json()
        assert "horizon_1_day" in data
        assert "horizon_3_days" in data
        assert "horizon_7_days" in data
        assert "horizon_14_days" in data
        assert data["label"] == "EXPECTED — not actual bank receipts"

    def test_forecast_upcoming_returns_200(self):
        r = client.get("/api/forecast/upcoming")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cash-Gap Alert Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCashGapAlerts:
    def test_alerts_summary_returns_200(self):
        r = client.get("/api/forecast/alerts/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_open" in data
        assert "critical_count" in data
        assert "high_count" in data
        assert "medium_count" in data
        assert "low_count" in data
        assert "total_risk_paise" in data
        assert "total_risk_inr" in data
        assert "by_type" in data

    def test_alerts_list_returns_200(self):
        r = client.get("/api/forecast/alerts")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data

    def test_alerts_filter_by_severity(self):
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            r = client.get(f"/api/forecast/alerts?severity={sev}")
            assert r.status_code == 200

    def test_acknowledge_nonexistent_alert(self):
        r = client.patch("/api/forecast/alerts/NONEXISTENT/acknowledge", json={"notes": "test"})
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 3. Audit Trail Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditTrail:
    def test_audit_events_list_returns_200(self):
        r = client.get("/api/audit/events")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data

    def test_audit_events_entity_filter(self):
        r = client.get("/api/audit/events?entity_type=SYSTEM")
        assert r.status_code == 200

    def test_audit_events_event_type_filter(self):
        r = client.get("/api/audit/events?event_type=ENGINE_RUN")
        assert r.status_code == 200

    def test_audit_trail_for_entity_returns_200(self):
        r = client.get("/api/audit/events/FORECAST_ENGINE")
        assert r.status_code == 200

    def test_run_forecast_logs_audit_event(self):
        """Verify that running the forecast engine creates audit events."""
        client.post("/api/forecast/run")
        r = client.get("/api/audit/events?entity_type=SYSTEM&event_type=ENGINE_RUN")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    def test_audit_service_log_event(self):
        """Test the audit trail service directly."""
        from app.services.audit.trail import log_event, get_events_for_entity

        db = get_db_session()
        event = log_event(
            db=db,
            entity_type="EXCEPTION_CASE",
            entity_id="TEST-CASE-001",
            event_type="STATUS_CHANGE",
            actor="test_user",
            from_value={"status": "OPEN"},
            to_value={"status": "IN_REVIEW"},
            notes="Test audit entry",
        )
        db.commit()

        assert event.event_id.startswith("AUD-")
        assert event.entity_type == "EXCEPTION_CASE"
        assert event.entity_id == "TEST-CASE-001"
        assert event.event_type == "STATUS_CHANGE"
        assert event.from_value == {"status": "OPEN"}
        assert event.to_value == {"status": "IN_REVIEW"}

        # Verify retrieval
        events = get_events_for_entity(db, "TEST-CASE-001", "EXCEPTION_CASE")
        assert len(events) >= 1
        assert any(e.event_id == event.event_id for e in events)
        db.close()

    def test_audit_events_are_immutable(self):
        """Events must not expose DELETE or UPDATE endpoints."""
        # No delete endpoint should exist
        r = client.delete("/api/audit/events/1")
        assert r.status_code in [404, 405]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Evaluation Dashboard Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluation:
    def test_metrics_returns_200(self):
        r = client.get("/api/evaluation/metrics")
        assert r.status_code == 200

    def test_metrics_structure(self):
        r = client.get("/api/evaluation/metrics")
        data = r.json()
        required_sections = [
            "generated_at",
            "note",
            "reconciliation",
            "settlement_calculations",
            "refund_reconciliation",
            "tax_reconciliation",
            "exception_detection",
            "resolution_performance",
            "audit_trail",
            "payment_posture",
            "ground_truth",
        ]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"

    def test_ground_truth_is_evaluation_only(self):
        """Ground truth disclaimer must be present."""
        r = client.get("/api/evaluation/metrics")
        data = r.json()
        gt = data["ground_truth"]
        assert "note" in gt
        assert "available" in gt
        # The note must indicate evaluation-only use
        assert "production" in gt["note"].lower() or "evaluation" in gt["note"].lower()

    def test_reconciliation_metrics_non_negative(self):
        r = client.get("/api/evaluation/metrics")
        data = r.json()
        recon = data["reconciliation"]
        assert recon["total_records"] >= 0
        assert recon["matched"] >= 0
        assert 0.0 <= recon["accuracy_pct"] <= 100.0

    def test_exception_detection_metrics(self):
        r = client.get("/api/evaluation/metrics")
        data = r.json()
        exc = data["exception_detection"]
        assert exc["total_orders"] >= 0
        assert exc["total_exceptions"] >= 0
        assert 0.0 <= exc["detection_rate_pct"] <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Model Integrity Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase4Models:
    def test_settlement_forecast_model_exists(self):
        from app.models.models import SettlementForecast
        assert SettlementForecast.__tablename__ == "settlement_forecasts"

    def test_cash_gap_alert_model_exists(self):
        from app.models.models import CashGapAlert
        assert CashGapAlert.__tablename__ == "cash_gap_alerts"

    def test_audit_trail_event_model_exists(self):
        from app.models.models import AuditTrailEvent
        assert AuditTrailEvent.__tablename__ == "audit_trail_events"

    def test_all_phase4_tables_created(self):
        """Verify all Phase 4 tables are in the DB."""
        from sqlalchemy import inspect
        insp = inspect(engine_test)
        tables = set(insp.get_table_names())
        for expected in ["settlement_forecasts", "cash_gap_alerts", "audit_trail_events"]:
            assert expected in tables, f"Missing table: {expected}"

    def test_version(self):
        r = client.get("/")
        data = r.json()
        assert data["version"] == "4.0.0"
