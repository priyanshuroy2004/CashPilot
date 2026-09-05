# CASHpilot AI — Phase 1 Foundation

> Finance Dashboard + Reconciliation Engine for e-commerce merchants.

## What's in Phase 1

| Layer | Contents |
|---|---|
| **Backend** | FastAPI + SQLAlchemy + PostgreSQL, 7-table schema |
| **Frontend** | Next.js 16 + TypeScript + Tailwind CSS shell with sidebar navigation |
| **Data** | Synthetic demo dataset (400 orders, 338 payments, 35 settlements, 60 bank txns) |
| **APIs** | `GET /api/health`, `POST /api/demo/load`, `GET /api/demo/status` |

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |
| PostgreSQL | 14+ (or Docker) |

---

## Quick Start

### 1 — Clone / navigate to the project

```bash
cd "CASHpilot AI"
```

### 2 — Start PostgreSQL

**Option A — Docker (recommended for local dev):**
```bash
docker compose up -d
```
This starts a PostgreSQL container at `localhost:5432` with credentials:
- DB: `cashpilot`, User: `cashpilot`, Password: `cashpilot_dev_password`

**Option B — Existing PostgreSQL / Supabase:**
Create a database and update `DATABASE_URL` in `backend/.env`.

---

### 3 — Backend Setup

```bash
cd backend
```

**Create a `.env` file** (copy from template):
```bash
cp .env.example .env
# Edit DATABASE_URL if needed
```

**Install Python dependencies:**
```bash
pip install -r requirements.txt
```

**Start the API server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will automatically create all database tables on first startup.

Verify it works:
```
GET http://localhost:8000/api/health
```

API docs available at: `http://localhost:8000/docs`

---

### 4 — Generate Demo Data

Run the data generation script from the **project root**:

```bash
python backend/scripts/generate_demo_data.py
```

This creates:
- `data/demo/orders.csv` — 400 synthetic orders
- `data/demo/payments.csv` — 338 payments (various statuses)
- `data/demo/settlements.csv` — 35 Razorpay-style settlements
- `data/demo/settlement_lines.csv` — 303 settlement line items
- `data/demo/bank_statement.csv` — 60 bank transactions
- `data/ground_truth/ground_truth.csv` — 368 expected reconciliation results (dev testing only)

> ⚠️ **ground_truth.csv is for developer testing ONLY.** The application never loads this into the database.

---

### 5 — Load Demo Data into PostgreSQL

Use the API (after the backend is running):

```bash
curl -X POST http://localhost:8000/api/demo/load
```

Or use the frontend Data page (see step 6).

Expected response:
```json
{
  "success": true,
  "message": "Demo data loaded successfully.",
  "orders": 400,
  "payments": 338,
  "settlements": 35,
  "settlement_lines": 303,
  "bank_transactions": 60
}
```

---

### 6 — Frontend Setup

```bash
cd frontend
```

**Create a `.env.local` file:**
```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

**Start the dev server:**
```bash
npm run dev
```

Frontend runs at: `http://localhost:3000`

Navigate to the **Data** tab → click **Load Demo Merchant Data** to load the dataset.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://cashpilot:cashpilot_dev_password@localhost:5432/cashpilot` | PostgreSQL connection string |
| `BACKEND_HOST` | `0.0.0.0` | Uvicorn bind host |
| `BACKEND_PORT` | `8000` | Uvicorn bind port |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## Database Schema

7 tables created automatically on backend startup:

| Table | Purpose |
|---|---|
| `orders` | E-commerce orders |
| `payments` | Payment captures (Razorpay-style IDs) |
| `settlements` | Settlement batches with UTR numbers |
| `settlement_lines` | Per-payment settlement detail |
| `bank_transactions` | Bank statement entries |
| `reconciliation_results` | (Empty in Phase 1 — schema ready for Phase 2) |
| `data_imports` | Import audit log |

All monetary amounts are stored as **BIGINT (paise)** — 1 INR = 100 paise — to avoid floating-point errors.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check — backend + DB connectivity |
| `POST` | `/api/demo/load` | Clear all data and reload from demo CSVs |
| `GET` | `/api/demo/status` | Current row counts for all tables |
| `GET` | `/docs` | Interactive Swagger UI |
| `GET` | `/redoc` | ReDoc API documentation |

---

## Dataset Design

The demo dataset represents **one coherent fictional Indian e-commerce merchant** over 2024.

### Linkage Chain
```
ORD-10021
    ↓
pay_abc123xyz...
    ↓
SETL-9015
    ↓
UTR-782938...
    ↓
BANK-0042
```

### Exception Cases Included

| Exception Type | Count | Description |
|---|---|---|
| `ORDER_WITHOUT_PAYMENT` | 10 | Paid orders with no payment record |
| `PAYMENT_AMOUNT_MISMATCH` | 5 | Payment amount differs from order |
| `FAILED_PAYMENT` | 10 | Payment failed, order marked paid |
| `DUPLICATE_PAYMENT` | 5 | One failed + one captured attempt |
| `PAYMENT_WITHOUT_ORDER` | 8 | Orphan captured payments |
| `PAYMENT_NOT_IN_SETTLEMENT` | 5 | Captured payments not in any settlement |
| `SETTLEMENT_MISSING_IN_BANK` | 4 | No bank credit for settlement |
| `SETTLEMENT_BANK_AMOUNT_MISMATCH` | 2 | Bank credit amount differs |
| `DELAYED_BANK_CREDIT` | 3 | Credit arrives 8–14 days late |
| `ORPHAN_BANK_CREDIT` | 4 | Bank credits with no settlement match |

Normal (matched) records: ~80% of the dataset.

---

## Project Structure

```
CASHpilot AI/
├── frontend/                    # Next.js 16 + TypeScript + Tailwind
│   ├── app/
│   │   ├── layout.tsx           # Root layout with sidebar
│   │   ├── page.tsx             # Overview (Phase 2 placeholder)
│   │   ├── data/page.tsx        # Data management page
│   │   ├── reconciliation/      # Phase 2 placeholder
│   │   └── exceptions/          # Phase 2 placeholder
│   ├── components/
│   │   └── Sidebar.tsx          # Navigation sidebar
│   ├── lib/api.ts               # Typed API client
│   └── types/index.ts           # TypeScript types
│
├── backend/                     # Python FastAPI
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── database/            # SQLAlchemy engine + session
│   │   ├── models/              # ORM models (7 tables)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── health.py        # GET /api/health
│   │   │   └── demo.py          # POST /api/demo/load, GET /api/demo/status
│   │   └── services/
│   │       ├── data_ingestion/  # CSV loader service
│   │       ├── schema_normalizer/  # (Phase 2+)
│   │       ├── reconciliation/  # (Phase 2+)
│   │       ├── dashboard/       # (Phase 2+)
│   │       └── exceptions/      # Custom exception types
│   ├── scripts/
│   │   └── generate_demo_data.py  # Synthetic data generator
│   └── requirements.txt
│
├── data/
│   ├── demo/                    # Generated CSV files
│   │   ├── orders.csv
│   │   ├── payments.csv
│   │   ├── settlements.csv
│   │   ├── settlement_lines.csv
│   │   └── bank_statement.csv
│   └── ground_truth/
│       └── ground_truth.csv     # Dev testing only — NOT loaded to DB
│
├── docker-compose.yml           # Local PostgreSQL
└── README.md
```

---

## What's NOT in Phase 1

- ❌ Reconciliation engine (Phase 2)
- ❌ AI / Copilot (Phase 3+)
- ❌ Forecasting (Phase 3+)
- ❌ Money Lineage Graph (Phase 3+)
- ❌ Case management (Phase 3+)
- ❌ Tax matching / Refunds analysis (Phase 3+)

---

## Development Notes

- **Money arithmetic**: All amounts are stored and computed as `BIGINT` paise. Never use floats for financial values.
- **Ground truth**: `ground_truth.csv` is for testing reconciliation accuracy in Phase 2. Never load it into the database.
- **Data regeneration**: Re-running `generate_demo_data.py` produces identical output (seeded with `random.seed(42)`).
- **CORS**: Backend allows `localhost:3000` by default. Set `FRONTEND_URL` env var for other origins.
