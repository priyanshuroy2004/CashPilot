"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getDashboardOverview,
  runReconciliation,
  loadDemoData,
} from "@/lib/api";
import type { DashboardOverviewResponse } from "@/types";
import ExecutiveBriefingCard from "@/components/ai/ExecutiveBriefingCard";
import FinancialAssistantDrawer from "@/components/ai/FinancialAssistantDrawer";

function formatPaiseToRupees(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "₹0.00";
  const rupees = paise / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(rupees);
}

export default function OverviewPage() {
  const [data, setData] = useState<DashboardOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [reconciling, setReconciling] = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboardOverview();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard overview.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const handleRunReconciliation = async () => {
    setReconciling(true);
    setSuccessMsg(null);
    setError(null);
    try {
      await runReconciliation(1);
      setSuccessMsg("Reconciliation completed and dashboard updated!");
      await fetchDashboard();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err?.message || "Reconciliation failed.");
    } finally {
      setReconciling(false);
    }
  };

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    setSuccessMsg(null);
    setError(null);
    try {
      const res = await loadDemoData();
      await runReconciliation(1);
      setSuccessMsg(
        `Loaded ${res.orders} orders, ${res.payments} payments, ${res.settlements} settlements! Reconciliation run completed.`
      );
      await fetchDashboard();
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || "Failed to load demo data.");
    } finally {
      setLoadingDemo(false);
    }
  };

  // Calculations (100% strictly preserved)
  const op = data?.orders_payments || {
    matched: 0,
    amount_mismatch: 0,
    payment_missing: 0,
    order_missing: 0,
    failed: 0,
    needs_review: 0,
    total: 0,
  };

  const sb = data?.settlements_bank || {
    matched: 0,
    pending: 0,
    mismatch: 0,
    needs_review: 0,
    total: 0,
  };

  const opMatchRate =
    op.total > 0 ? ((op.matched / op.total) * 100).toFixed(1) : "0.0";
  const sbMatchRate =
    sb.total > 0 ? ((sb.matched / sb.total) * 100).toFixed(1) : "0.0";

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 bg-[#F8FAFC]">
      {/* ─── Header & Action Toolbar ─────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Finance Overview
            </h1>
            {data?.has_data ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="w-2 h-2 rounded-full bg-[#00B574] animate-pulse" />
                Live Database
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-[#0C5ADB] border border-blue-200">
                <span className="w-2 h-2 rounded-full bg-[#0C5ADB] animate-pulse" />
                Demo Ready
              </span>
            )}
          </div>
          <p className="text-slate-500 mt-1 text-xs sm:text-sm max-w-2xl leading-relaxed">
            Real-time financial reconciliation metrics and cash audit across payment gateways & bank accounts.
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setIsAssistantOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-xs bg-white hover:bg-slate-50 text-slate-800 shadow-sm border border-emerald-300 transition-all transform hover:scale-[1.01] cursor-pointer"
          >
            <div className="w-4 h-4 text-[#00B574] flex items-center justify-center">
              <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
              </svg>
            </div>
            <span>Ask AI</span>
          </button>

          <button
            onClick={handleRunReconciliation}
            disabled={reconciling || loading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs tracking-wide bg-[#0C5ADB] hover:bg-[#0944A8] text-white shadow-md shadow-blue-900/20 disabled:opacity-50 transition-all cursor-pointer"
          >
            {reconciling ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Reconciling...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
                <span>Run Reconciliation</span>
              </>
            )}
          </button>

          <Link
            href="/exceptions"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-xs text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 hover:border-amber-300 transition shadow-sm"
          >
            <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            <span>Exceptions</span>
          </Link>
        </div>
      </div>

      {/* ─── Notifications ───────────────────────────────────────────────── */}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs sm:text-sm flex items-center gap-3 animate-fadeIn shadow-sm">
          <svg className="w-5 h-5 text-emerald-600 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-semibold">{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs sm:text-sm flex items-center gap-3 animate-fadeIn shadow-sm">
          <svg className="w-5 h-5 text-rose-600 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <span className="font-semibold">{error}</span>
        </div>
      )}

      {/* ─── Empty State / Onboarding Hero ───────────────────────────────── */}
      {!loading && !data?.has_data && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-10 md:p-12 text-center shadow-md relative overflow-hidden">
          <div className="relative z-10 max-w-2xl mx-auto space-y-4">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-[#0C5ADB] border border-blue-200">
              <span className="w-2 h-2 rounded-full bg-[#0C5ADB] animate-pulse" />
              <span>Razorpay Hackathon Demo Ready</span>
            </div>

            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Welcome to CASHpilot AI
            </h2>

            <p className="text-slate-600 text-xs sm:text-sm md:text-base leading-relaxed max-w-xl mx-auto">
              This is a demo instance of <span className="text-slate-900 font-semibold">CASHpilot AI</span> built for the Razorpay ecosystem. Click <span className="text-[#0C5ADB] font-semibold">“Load Demo Merchant Data”</span> to explore automated settlement matching, fee audits, and exception tracking — or <span className="text-[#00B574] font-semibold">upload your own CSV files</span> to audit live business ledgers.
            </p>

            {/* Dual Options Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left max-w-xl mx-auto pt-4">
              {/* Option 1: Load Demo */}
              <button
                onClick={handleLoadDemo}
                disabled={loadingDemo}
                className="group p-5 rounded-xl bg-blue-50/50 hover:bg-blue-50 border border-blue-200 hover:border-[#0C5ADB] transition-all duration-200 shadow-xs flex flex-col justify-between cursor-pointer text-left"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#0C5ADB]">Instant Setup</span>
                    <div className="w-8 h-8 rounded-lg bg-blue-100/70 border border-blue-200 flex items-center justify-center text-[#0C5ADB] group-hover:scale-110 transition-transform">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
                      </svg>
                    </div>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 mb-1.5 group-hover:text-[#0C5ADB] transition-colors">
                    {loadingDemo ? "Loading Dataset..." : "Load Demo Merchant Data"}
                  </h3>
                  <p className="text-xs text-slate-500 leading-normal">
                    Explore with simulated checkout orders, Razorpay payouts, GST breakdowns, and bank credits.
                  </p>
                </div>
                <span className="mt-5 inline-flex items-center gap-1.5 text-xs font-bold text-[#0C5ADB] group-hover:translate-x-0.5 transition-all">
                  {loadingDemo ? "Loading Data..." : "Load Demo Dataset →"}
                </span>
              </button>

              {/* Option 2: Upload Own Data */}
              <Link
                href="/data"
                className="group p-5 rounded-xl bg-slate-50 hover:bg-slate-100/80 border border-slate-200 hover:border-slate-300 transition-all duration-200 shadow-xs flex flex-col justify-between text-left"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Live Merchant</span>
                    <div className="w-8 h-8 rounded-lg bg-slate-200/60 border border-slate-300 flex items-center justify-center text-slate-700 group-hover:scale-110 transition-transform">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                      </svg>
                    </div>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 mb-1.5 group-hover:text-slate-800 transition-colors">
                    Upload Your Own Data
                  </h3>
                  <p className="text-xs text-slate-500 leading-normal">
                    Import your custom CSV files for orders, payment reports, gateway settlements, or bank statements.
                  </p>
                </div>
                <span className="mt-5 inline-flex items-center gap-1.5 text-xs font-bold text-slate-700 group-hover:translate-x-0.5 transition-all">
                  Go to CSV Uploader →
                </span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* ─── Executive CFO Briefing Card ─────────────────────────────────── */}
      {data?.has_data && (
        <div>
          <ExecutiveBriefingCard />
        </div>
      )}

      {/* ─── Primary Financial KPI Cards ─────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Orders */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Total Orders
            </span>
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 text-[#0C5ADB] flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0l-3-3m3 3l3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
              </svg>
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {loading ? "..." : (data?.total_orders ?? 0).toLocaleString()}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500 font-mono">
            Gross Value: <span className="text-[#0C5ADB] font-semibold">{formatPaiseToRupees(data?.total_orders_amount)}</span>
          </p>
        </div>

        {/* Captured Payments */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Captured Payments
            </span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 text-[#00B574] flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z" />
              </svg>
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {loading ? "..." : (data?.total_captured_payments ?? 0).toLocaleString()}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500 font-mono">
            Collected: <span className="text-[#00B574] font-semibold">{formatPaiseToRupees(data?.total_captured_amount)}</span>
          </p>
        </div>

        {/* Settlements (Payouts) */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Settlements (Payouts)
            </span>
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 text-[#0C5ADB] flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {loading ? "..." : (data?.total_settlements ?? 0).toLocaleString()}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500 font-mono">
            Net Payout: <span className="text-[#0C5ADB] font-semibold">{formatPaiseToRupees(data?.total_settlements_net)}</span>
          </p>
        </div>

        {/* Bank Credits */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Bank Credits
            </span>
            <div className="w-9 h-9 rounded-xl bg-teal-50 border border-teal-200 text-teal-600 flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.5m-15 10.5V10.5M3 21h18" />
              </svg>
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {loading ? "..." : (data?.total_bank_credits ?? 0).toLocaleString()}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500 font-mono">
            Deposited: <span className="text-teal-700 font-semibold">{formatPaiseToRupees(data?.total_bank_credits_amount)}</span>
          </p>
        </div>
      </div>

      {/* ─── Secondary Reconciliation Status KPI Cards ──────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Matched Records */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Matched Records
            </span>
            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              Verified
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-emerald-700 font-mono tracking-tight">
              {loading ? "..." : (data?.matched_records ?? 0).toLocaleString()}
            </span>
            <span className="text-xs text-slate-500">records</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Strict 1-paise tolerance verification
          </p>
        </div>

        {/* Pending / Missing */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Pending / In-Transit
            </span>
            <span className="text-[10px] font-bold text-[#0C5ADB] bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
              Unmatched
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-[#0C5ADB] font-mono tracking-tight">
              {loading ? "..." : (data?.pending_missing_records ?? 0).toLocaleString()}
            </span>
            <span className="text-xs text-slate-500">cases</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Missing captures & in-transit payouts
          </p>
        </div>

        {/* Exceptions */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Actionable Exceptions
            </span>
            <span className="text-[10px] font-bold text-amber-800 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200">
              Actionable
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-amber-700 font-mono tracking-tight">
              {loading ? "..." : (data?.exception_count ?? 0).toLocaleString()}
            </span>
            <span className="text-xs text-slate-500">flagged</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Mismatches, fee anomalies & review cases
          </p>
        </div>

        {/* Total Value at Risk */}
        <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 sm:p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider">
              Total Value at Risk
            </span>
            <span className="text-[10px] font-bold text-rose-700 bg-rose-100/80 px-2.5 py-0.5 rounded-full border border-rose-200">
              High Priority
            </span>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-rose-700 font-mono tracking-tight">
              {loading ? "..." : formatPaiseToRupees(data?.value_at_risk)}
            </span>
          </div>
          <p className="mt-2 text-xs text-rose-600">
            Discrepant cash requiring audit attention
          </p>
        </div>
      </div>

      {/* ─── Reconciliation Summary Cards ───────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Order ↔ Payment Breakdown */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>Order → Payment Reconciliation</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Matches customer checkout orders to payment gateway captures.
              </p>
            </div>
            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 font-mono">
              {opMatchRate}% Match
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-100 rounded-full h-3 mb-6 overflow-hidden flex shadow-inner">
            <div
              style={{ width: `${op.total > 0 ? (op.matched / op.total) * 100 : 0}%` }}
              className="bg-[#00B574] h-full transition-all duration-500"
              title={`Matched: ${op.matched}`}
            />
            <div
              style={{ width: `${op.total > 0 ? (op.amount_mismatch / op.total) * 100 : 0}%` }}
              className="bg-amber-400 h-full transition-all duration-500"
              title={`Amount Mismatch: ${op.amount_mismatch}`}
            />
            <div
              style={{ width: `${op.total > 0 ? (op.payment_missing / op.total) * 100 : 0}%` }}
              className="bg-[#0C5ADB] h-full transition-all duration-500"
              title={`Payment Missing: ${op.payment_missing}`}
            />
            <div
              style={{ width: `${op.total > 0 ? (op.failed / op.total) * 100 : 0}%` }}
              className="bg-rose-500 h-full transition-all duration-500"
              title={`Failed Payment: ${op.failed}`}
            />
            <div
              style={{ width: `${op.total > 0 ? (op.needs_review / op.total) * 100 : 0}%` }}
              className="bg-purple-500 h-full transition-all duration-500"
              title={`Needs Review: ${op.needs_review}`}
            />
          </div>

          {/* Counters Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Matched</span>
              <span className="text-lg font-bold text-emerald-700 font-mono">{op.matched}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Payment Missing</span>
              <span className="text-lg font-bold text-[#0C5ADB] font-mono">{op.payment_missing}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Amount Mismatch</span>
              <span className="text-lg font-bold text-amber-700 font-mono">{op.amount_mismatch}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Failed Payment</span>
              <span className="text-lg font-bold text-rose-600 font-mono">{op.failed}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Needs Review</span>
              <span className="text-lg font-bold text-purple-700 font-mono">{op.needs_review}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Total Checked</span>
              <span className="text-lg font-bold text-slate-900 font-mono">{op.total}</span>
            </div>
          </div>
        </div>

        {/* Settlement ↔ Bank Breakdown */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>Settlement → Bank Reconciliation</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Matches gateway net payouts (gross - fee - tax) to bank statement credits.
              </p>
            </div>
            <span className="text-xs font-bold text-teal-700 bg-teal-50 px-3 py-1 rounded-full border border-teal-200 font-mono">
              {sbMatchRate}% Match
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-100 rounded-full h-3 mb-6 overflow-hidden flex shadow-inner">
            <div
              style={{ width: `${sb.total > 0 ? (sb.matched / sb.total) * 100 : 0}%` }}
              className="bg-[#00B574] h-full transition-all duration-500"
              title={`Matched: ${sb.matched}`}
            />
            <div
              style={{ width: `${sb.total > 0 ? (sb.pending / sb.total) * 100 : 0}%` }}
              className="bg-[#0C5ADB] h-full transition-all duration-500"
              title={`Pending Bank Credit: ${sb.pending}`}
            />
            <div
              style={{ width: `${sb.total > 0 ? (sb.mismatch / sb.total) * 100 : 0}%` }}
              className="bg-rose-500 h-full transition-all duration-500"
              title={`Mismatch: ${sb.mismatch}`}
            />
            <div
              style={{ width: `${sb.total > 0 ? (sb.needs_review / sb.total) * 100 : 0}%` }}
              className="bg-purple-500 h-full transition-all duration-500"
              title={`Needs Review: ${sb.needs_review}`}
            />
          </div>

          {/* Counters Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Matched</span>
              <span className="text-lg font-bold text-emerald-700 font-mono">{sb.matched}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Pending Credit</span>
              <span className="text-lg font-bold text-[#0C5ADB] font-mono">{sb.pending}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Bank Mismatch</span>
              <span className="text-lg font-bold text-rose-600 font-mono">{sb.mismatch}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-[11px] text-slate-500 block font-medium">Total Checked</span>
              <span className="text-lg font-bold text-slate-900 font-mono">{sb.total}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Quick Navigation Cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/reconciliation"
          className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-[#0C5ADB] shadow-sm hover:shadow-md transition-all duration-200 group"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-slate-900 group-hover:text-[#0C5ADB] transition-colors flex items-center gap-2">
              <span>⚡ Reconciliation Workspace</span>
            </h3>
            <span className="text-slate-400 group-hover:translate-x-1 group-hover:text-[#0C5ADB] transition-all">→</span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Drill down into individual order-payment records, settlement lines, and bank match hierarchies.
          </p>
        </Link>

        <Link
          href="/exceptions"
          className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-amber-400 shadow-sm hover:shadow-md transition-all duration-200 group"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-slate-900 group-hover:text-amber-700 transition-colors flex items-center gap-2">
              <span>⚠️ Exceptions Workspace</span>
            </h3>
            <span className="text-slate-400 group-hover:translate-x-1 group-hover:text-amber-700 transition-all">→</span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Investigate financial discrepancies, duplicate retry attempts, and missing bank credits by severity.
          </p>
        </Link>

        <Link
          href="/data"
          className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-teal-400 shadow-sm hover:shadow-md transition-all duration-200 group"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-slate-900 group-hover:text-teal-700 transition-colors flex items-center gap-2">
              <span>📂 Data Import & CSV Upload</span>
            </h3>
            <span className="text-slate-400 group-hover:translate-x-1 group-hover:text-teal-700 transition-all">→</span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Upload custom orders, payments, settlements, and bank statements with auto schema validation.
          </p>
        </Link>
      </div>

      {/* ─── Financial Assistant Sliding Drawer ─────────────────────────── */}
      <FinancialAssistantDrawer
        isOpen={isAssistantOpen}
        onClose={() => setIsAssistantOpen(false)}
      />
    </div>
  );
}
