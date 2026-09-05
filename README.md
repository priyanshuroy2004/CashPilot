# CASHpilot AI — Autonomous Finance Controller & Zero-Loss Reconciliation Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Autonomous Finance Controller for high-volume Razorpay merchants.**  
> Built for the Razorpay Hackathon — pairs deterministic 1-paise zero-loss reconciliation with grounded AI root-cause investigation, interactive money lineage graphs, and forward cash-gap forecasting.

---

## 📌 Executive Summary

High-volume digital merchants face continuous, silent **revenue leakage**:
* **Gateway Fee Creep**: Discrepancies between contracted MDR rates (e.g. 2.0%) and actual deductions (2.36%+).
* **Tax Mismatches**: Dropped GST (18%) line items on settlement statements.
* **Unsettled Backlog**: Captured customer payments that never reach the merchant's bank account.
* **Refund Gaps**: Customer refunds debited by the gateway without corresponding ledger adjustments.

**CASHpilot AI** replaces manual spreadsheet audits with an enterprise-grade automated reconciliation platform styled with the **Razorpay Enterprise Design System (Razorpay Blade)**.

---

## 🌟 Key Capabilities

### 1. ⚡ Deterministic Multi-Pass Reconciliation Engine
* **Layer 1 (Orders ↔ Payments)**: Validates order creation, capture timestamps, and gateway payment IDs.
* **Layer 2 (Settlements ↔ Bank Credits)**: Matches settlement batches to bank statement deposits via UTR numbers.
* **Deterministic 1-Paise Tolerance**: Flags any monetary variance $> \text{₹}0.01$, eliminating floating-point rounding errors by performing all financial arithmetic in integer **paise**.

### 2. 📑 Financial Integrity Suite & Settlement Breakdown
* Enforces the mathematical settlement formula on every payout:
  $$\text{Gross Amount} - \text{Gateway Fee} - \text{GST Tax (18\%)} + \text{Refund Adjustments} = \text{Net Bank Credit}$$
* Verifies MDR percentages across payment methods (UPI, Cards, Netbanking, Wallets).
* Audits refund ledger reconciliation and tax reporting lines.

### 3. 🧠 Grounded AI Root-Cause Intelligence ("Ask AI")
* **Zero-Hallucination Guarantee**: The AI model is strictly grounded on auditable database evidence; it never invents transaction numbers or figures.
* **Case Investigation Workspace**: Automatically groups transaction anomalies into actionable audit cases (`CASE-SETL-9019`, etc.).
* **Interactive Money Lineage Graph**: Visual node-and-edge graph tracing the end-to-end journey:
  $$\text{Order} \longrightarrow \text{Payment} \longrightarrow \text{Settlement} \longrightarrow \text{UTR} \longrightarrow \text{Bank Credit}$$
* **Ask AI Copilot Drawer**: Slide-out assistant providing instant answers to CFO and controller queries.

### 4. 📈 Forward Settlement Forecast & Cash-Gap Intelligence
* **Multi-Horizon Projections**: Projects expected forward cash inflow across **1-Day, 3-Day, 7-Day, and 14-Day** cumulative settlement windows.
* **Overdue Backlog Detection**: Automatically identifies unsettled captured payments that missed gateway settlement SLAs ($T+2$ to $T+3$) and categorizes them as overdue risk.
* **Automated Gap Alerts**: Proactive alert triage with severity scoring (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and one-click user acknowledgment.
* **Immutable Compliance Audit Trail**: Every status transition (`OPEN` $\to$ `ACKNOWLEDGED` $\to$ `RESOLVED`) is permanently recorded in `audit_trail_events`.

### 5. 📂 Flexible Data Ingestion & Demo Mode
* **Universal CSV Dropzone**: Drag-and-drop ingestion for production Orders, Payments, Settlements, and Bank CSV files with automated schema normalization.
* **1-Click Demo Loader**: Instant evaluation with a realistic 1,000-transaction merchant dataset featuring real-world edge cases.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Next.js 15+ Frontend (Razorpay Blade UI)             │
│  - Overview Dashboard    - Multi-Pass Recon Ledger   - Case Workspace │
│  - Financial Integrity   - Forward Cash Forecast     - Ask AI Copilot │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend Application Engine                  │
│  ├── Reconciliation Engine   (Order-Payment & Settlement-Bank Matcher) │
│  ├── Financial Calculator    (Gross - Fee - Tax + Refund = Net)        │
│  ├── Exception Detector      (Rule-based anomaly classifier)           │
│  ├── Forecast & Gap Engine   (Gateway lag & overdue backlog modeling)  │
│  ├── AI Root-Cause Service   (Grounded evidence builder + LLM router)  │
│  └── Audit Trail Service     (Append-only immutable event log)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy ORM
┌───────────────────────────────────▼────────────────────────────────────┐
│                 PostgreSQL Database (17 Core Tables)                   │
│  Orders · Payments · Settlements · Settlement Lines · Bank Txns ·      │
│  Refunds · Ledger Entries · Calculations · Tax & Refund Recon ·        │
│  Exceptions · Shipments · Forecasts · Gap Alerts · Audit Events        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | Next.js 15+ (App Router), TypeScript, Tailwind CSS v4, Lucide Icons, Canvas/SVG Graphs |
| **Design System** | Razorpay Enterprise Blade (`#0C2340` Navy, `#0C5ADB` Royal Blue, `#00B574` Mint) |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Uvicorn |
| **Database** | PostgreSQL 15+ (Integer Paise arithmetic for zero loss) |
| **AI / LLM** | OpenAI / Gemini / Claude APIs + Deterministic Rule Fallback Engine |
| **DevOps** | Docker Compose, GitHub Actions |

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/priyanshuroy2004/CashPilot.git
cd CashPilot
```

### 2. Start PostgreSQL (Docker)
```bash
docker compose up -d
```
*Starts PostgreSQL on `localhost:5432` (`db: cashpilot`, `user: cashpilot`, `password: cashpilot_dev_password`).*

### 3. Backend Setup
```bash
cd backend

# Create local environment config
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
* Interactive Swagger Docs: `http://localhost:8000/docs`
* Health Check: `http://localhost:8000/api/health`

### 4. Frontend Setup
```bash
cd ../frontend

# Create local environment config
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
* Access CASHpilot UI: **`http://localhost:3000`**

### 5. Ingest Demo Merchant Data
Navigate to **`http://localhost:3000/data`** and click **"Load Demo Merchant Data"** (or trigger via API):
```bash
curl -X POST http://localhost:8000/api/demo/load
```

---

## 🧪 Automated Testing & Verification

CASHpilot includes a comprehensive test suite covering all phases of reconciliation, financial formulas, exception triage, and forward forecasting:

```bash
cd backend
pytest tests/
```

| Test Suite | Focus Area |
| :--- | :--- |
| `tests/test_phase1_e2e.py` | Ingestion pipelines, schema validation, and health checks |
| `tests/test_phase2a.py` | Net settlement formula, fee percentages, and 18% GST calculations |
| `tests/test_phase2b.py` | Exception cases, priority scoring, and status workflows |
| `tests/test_phase3.py` | Grounded AI explanations, non-hallucination guardrails, and evaluation benchmarks |
| `tests/test_phase4.py` | Forward settlement projections, cash-gap alerts, and audit trail idempotency |
| `tests/test_reconciliation.py` | 1-paise tolerance rules, UTR matching, and currency normalization |

---

## 📊 Database Schema Overview

All financial values are stored as **BIGINT (paise)** where ₹1.00 = 100 paise:

1. **`orders`**: Customer checkout orders.
2. **`payments`**: Gateway captures, auth states, methods (`pay_...`).
3. **`settlements`**: Razorpay settlement batches with bank UTRs (`SETL-...`).
4. **`settlement_lines`**: Itemized gross, fee, and tax per transaction.
5. **`bank_transactions`**: Bank feed credits and debits.
6. **`reconciliation_results`**: Deterministic match outcomes.
7. **`refunds`**: Customer refunds and adjustments.
8. **`ledger_entries`**: Merchant accounting ledger lines.
9. **`settlement_calculations`**: Mathematical net formula audit results.
10. **`tax_reconciliation_results`**: GST 18% compliance checks.
11. **`refund_reconciliation_results`**: Refund debit vs ledger matches.
12. **`shipments`**: Logistics fulfillment tracking.
13. **`financial_exceptions`**: Triage cases for anomalies.
14. **`settlement_forecasts`**: Rolling 1D, 3D, 7D, 14D projections.
15. **`cash_gap_alerts`**: Overdue settlement & missing bank deposit alerts.
16. **`audit_trail_events`**: Immutable event log.
17. **`data_imports`**: Audit records for uploaded CSV batches.

---

## 🎥 Video Demonstration & Pitch

A complete, timestamped walkthrough script designed for hackathon judges is available in the repository:
* 📄 **[Video Demonstration Script](video_demo_script.md)**

---

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
