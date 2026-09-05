# CASHpilot AI — Production Deployment Guide

Deploy CASHpilot AI to production in **under 5 minutes** for **100% free** using **Render** (Backend + PostgreSQL) and **Vercel** (Frontend).

---

## 🏗️ Architecture Overview

```text
┌────────────────────────────────────────────────────────┐
│               Frontend: Vercel (Free)                  │
│       https://your-cashpilot-app.vercel.app            │
└───────────────────────────┬────────────────────────────┘
                            │ NEXT_PUBLIC_API_URL
┌───────────────────────────▼────────────────────────────┐
│            Backend: Render Web Service (Free)          │
│       https://cashpilot-backend.onrender.com           │
└───────────────────────────┬────────────────────────────┘
                            │ DATABASE_URL
┌───────────────────────────▼────────────────────────────┐
│        Database: Render Managed PostgreSQL (Free)      │
│                  PostgreSQL 16                         │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Part 1: Deploy Backend + PostgreSQL on Render (2 Mins)

Render provides free hosting for both FastAPI and PostgreSQL, and your repository already includes a pre-configured `render.yaml` blueprint.

### Steps:
1. Log in to **[Render](https://dashboard.render.com/)** (sign in with your GitHub account `priyanshuroy2004`).
2. In the top navigation bar, click **New +** $\to$ select **Blueprint**.
3. Connect your repository: **`priyanshuroy2004/CashPilot`**.
4. Render will automatically detect `render.yaml`:
   * It creates a managed database: **`cashpilot-postgres`**
   * It creates a FastAPI web service: **`cashpilot-backend`**
5. Click **Apply**.
6. Wait 1–2 minutes for the build to finish. Once completed, copy your **Backend Service URL** (e.g., `https://cashpilot-backend-xxxx.onrender.com`).
7. Verify it is running by visiting:
   ```
   https://cashpilot-backend-xxxx.onrender.com/api/health
   ```
   *(You should see `{"status":"healthy","database":"connected","version":"1.0.0"}`)*.

---

## 🌐 Part 2: Deploy Frontend on Vercel (1 Min)

Vercel is the creator of Next.js and provides instant deployment with a global edge CDN.

### Steps:
1. Log in to **[Vercel](https://vercel.com/)** (sign in with your GitHub account).
2. Click **"Add New…"** $\to$ select **Project**.
3. Import your GitHub repository: **`priyanshuroy2004/CashPilot`**.
4. Configure the project settings:
   * **Framework Preset**: `Next.js` *(detected automatically)*
   * **Root Directory**: Click **Edit** $\to$ select **`frontend`** *(CRITICAL: do not leave at root!)*
5. Under **Environment Variables**, add:
   * **Key**: `NEXT_PUBLIC_API_URL`
   * **Value**: Your Render Backend URL from Part 1 (e.g., `https://cashpilot-backend-xxxx.onrender.com` — *no trailing slash*)
6. Click **Deploy**.
7. In ~60 seconds, your site will be live at `https://cashpilot-xxxx.vercel.app`!

---

## 📥 Part 3: Load Initial Demo Data into the Cloud Database

Once your live site is up:
1. Open your live Vercel URL in your browser: `https://cashpilot-xxxx.vercel.app`.
2. In the left navigation sidebar, click **Data Import** (`/data`).
3. Click the button: **"Load Demo Merchant Data"**.
4. The system will ingest all 1,000 synthetic merchant orders, payments, settlements, and bank credits into your cloud PostgreSQL database.
5. Head over to **Overview**, **Reconciliation**, **Exceptions**, and **Forecast & Alerts** — your live deployment is 100% operational!

---

## 🔒 Production Security Checklist

* [x] **Zero Credentials in Git**: `.env` and `.env.local` are strictly git-ignored.
* [x] **CORS Enabled for Vercel**: Backend automatically permits all `https://*.vercel.app` domains and custom frontend URLs.
* [x] **1-Paise Precision Guardrails**: Database amounts stored in integer paise (`BIGINT`) to prevent floating-point rounding discrepancies.
