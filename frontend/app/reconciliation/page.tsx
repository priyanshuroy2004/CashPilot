"use client";

import { useEffect, useState, useCallback } from "react";
import {
  runReconciliation,
  getReconciliationSummary,
  getOrderPaymentRecon,
  getSettlementBankRecon,
} from "@/lib/api";
import type {
  ReconciliationItem,
  ReconciliationSummaryResponse,
} from "@/types";

type ActiveTab = "orders_payments" | "settlements_bank";

const STATUS_CONFIG: Record<
  string,
  { label: string; bg: string; text: string; border: string; dot: string }
> = {
  MATCHED: {
    label: "MATCHED",
    bg: "bg-emerald-50",
    text: "text-emerald-800",
    border: "border-emerald-200",
    dot: "bg-[#00B574]",
  },
  MATCHED_WITH_TOLERANCE: {
    label: "TOLERANCE MATCH",
    bg: "bg-teal-50",
    text: "text-teal-800",
    border: "border-teal-200",
    dot: "bg-teal-600",
  },
  AMOUNT_MISMATCH: {
    label: "AMOUNT MISMATCH",
    bg: "bg-amber-50",
    text: "text-amber-800",
    border: "border-amber-200",
    dot: "bg-amber-500",
  },
  MISMATCH: {
    label: "BANK MISMATCH",
    bg: "bg-orange-50",
    text: "text-orange-800",
    border: "border-orange-200",
    dot: "bg-orange-500",
  },
  PAYMENT_MISSING: {
    label: "PAYMENT MISSING",
    bg: "bg-rose-50",
    text: "text-rose-800",
    border: "border-rose-200",
    dot: "bg-rose-500 animate-pulse",
  },
  ORDER_MISSING: {
    label: "ORPHAN PAYMENT",
    bg: "bg-rose-50",
    text: "text-rose-800",
    border: "border-rose-200",
    dot: "bg-rose-500",
  },
  FAILED_PAYMENT: {
    label: "FAILED PAYMENT",
    bg: "bg-red-50",
    text: "text-red-800",
    border: "border-red-200",
    dot: "bg-red-600",
  },
  PENDING_BANK_CREDIT: {
    label: "PENDING CREDIT",
    bg: "bg-blue-50",
    text: "text-blue-800",
    border: "border-blue-200",
    dot: "bg-[#0C5ADB]",
  },
  NEEDS_REVIEW: {
    label: "NEEDS REVIEW",
    bg: "bg-purple-50",
    text: "text-purple-800",
    border: "border-purple-200",
    dot: "bg-purple-600",
  },
};

function formatPaiseToRupees(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "—";
  const rupees = paise / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(rupees);
}

export default function ReconciliationPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("orders_payments");
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState<ReconciliationSummaryResponse | null>(null);
  const [items, setItems] = useState<ReconciliationItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 25;
  const [lastRunTime, setLastRunTime] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load summary and table data (100% preserved logic)
  const loadData = useCallback(async () => {
    try {
      setErrorMsg(null);
      const sum = await getReconciliationSummary();
      setSummary(sum);

      const offset = page * pageSize;
      if (activeTab === "orders_payments") {
        const res = await getOrderPaymentRecon(
          statusFilter,
          searchQuery,
          pageSize,
          offset
        );
        setItems(res.items);
        setTotalCount(res.total);
      } else {
        const res = await getSettlementBankRecon(
          statusFilter,
          searchQuery,
          pageSize,
          offset
        );
        setItems(res.items);
        setTotalCount(res.total);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load data");
    }
  }, [activeTab, statusFilter, searchQuery, page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Run reconciliation handler (100% preserved logic)
  async function handleRunRecon() {
    setRunning(true);
    setErrorMsg(null);
    try {
      const res = await runReconciliation(1); // 1 paise tolerance
      setLastRunTime(new Date().toLocaleTimeString());
      setSummary({
        orders_payments: res.orders_payments,
        settlements_bank: res.settlements_bank,
        total_records: res.total_records,
      });
      setPage(0);
      await loadData();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Reconciliation run failed");
    } finally {
      setRunning(false);
    }
  }

  const opSummary = summary?.orders_payments;
  const sbSummary = summary?.settlements_bank;

  const orderMatchRate =
    opSummary && opSummary.total > 0
      ? ((opSummary.matched / opSummary.total) * 100).toFixed(1)
      : "0.0";

  const settlementMatchRate =
    sbSummary && sbSummary.total > 0
      ? ((sbSummary.matched / sbSummary.total) * 100).toFixed(1)
      : "0.0";

  const totalExceptions =
    (opSummary?.amount_mismatch || 0) +
    (opSummary?.payment_missing || 0) +
    (opSummary?.order_missing || 0) +
    (opSummary?.failed || 0) +
    (opSummary?.needs_review || 0) +
    (sbSummary?.pending || 0) +
    (sbSummary?.mismatch || 0) +
    (sbSummary?.needs_review || 0);

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 bg-[#F8FAFC]">
      {/* ─── Header & Action Toolbar ─────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Deterministic Reconciliation Engine
            </h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-[#00B574] animate-pulse" />
              Live Engine
            </span>
          </div>
          <p className="text-slate-500 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
            Zero-hallucination, integer-paise matching across Orders ↔ Payments and Settlements ↔ Bank Credits.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {lastRunTime && (
            <span className="text-xs text-slate-500 font-mono flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-xs">
              <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Last run: {lastRunTime}</span>
            </span>
          )}
          <button
            id="run-recon-btn"
            onClick={handleRunRecon}
            disabled={running}
            className={`px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide transition-all duration-200 flex items-center gap-2 shadow-md cursor-pointer ${
              running
                ? "bg-slate-300 text-slate-600 cursor-not-allowed border border-slate-300"
                : "bg-[#0C5ADB] hover:bg-[#0944A8] text-white shadow-blue-900/20 active:scale-95"
            }`}
          >
            {running ? (
              <>
                <svg className="animate-spin w-4 h-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4}/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                <span>Reconciling…</span>
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
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs sm:text-sm flex items-center gap-3 shadow-xs">
          <svg className="w-5 h-5 text-rose-500 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <span className="font-semibold">{errorMsg}</span>
        </div>
      )}

      {/* ─── KPI Cards ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Order Match Rate */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Orders Reconciled
            </span>
            <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 font-mono">
              {orderMatchRate}%
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {opSummary?.matched ?? "—"}
            </span>
            <span className="text-xs text-slate-500 font-mono">
              / {opSummary?.total ?? "—"} total
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
            <span className="text-amber-700 font-medium font-mono">{opSummary?.amount_mismatch ?? 0} mismatch</span>
            <span>·</span>
            <span className="text-rose-600 font-medium font-mono">{opSummary?.payment_missing ?? 0} missing</span>
          </div>
        </div>

        {/* Settlement Match Rate */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Settlements Reconciled
            </span>
            <span className="text-[10px] font-bold text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded-full border border-teal-200 font-mono">
              {settlementMatchRate}%
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {sbSummary?.matched ?? "—"}
            </span>
            <span className="text-xs text-slate-500 font-mono">
              / {sbSummary?.total ?? "—"} total
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
            <span className="text-[#0C5ADB] font-medium font-mono">{sbSummary?.pending ?? 0} pending</span>
            <span>·</span>
            <span className="text-orange-700 font-medium font-mono">{sbSummary?.mismatch ?? 0} mismatch</span>
          </div>
        </div>

        {/* Total Exceptions */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Exceptions Found
            </span>
            <span className="text-[10px] font-bold text-amber-800 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200">
              Actionable
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-amber-700 font-mono tracking-tight">
              {totalExceptions}
            </span>
            <span className="text-xs text-slate-500">records</span>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            <span className="font-mono text-slate-800 font-semibold">{opSummary?.needs_review ?? 0}</span> review cases flagged
          </p>
        </div>

        {/* Financial Arithmetic Rule */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Matching Precision
            </span>
            <span className="text-[10px] font-bold text-[#0C5ADB] bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
              1 Paise
            </span>
          </div>
          <div className="mt-3">
            <span className="text-sm font-bold text-slate-900 block">
              Net Settlement Formula
            </span>
          </div>
          <p className="mt-2 text-[11px] text-slate-600 font-mono bg-slate-50 p-2 rounded-lg border border-slate-200 leading-relaxed">
            gross - fee - tax + adjustment = net
          </p>
        </div>
      </div>

      {/* ─── Main Table Card ─────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Tab Switcher & Filter Toolbar */}
        <div className="p-4 sm:p-5 border-b border-slate-200 bg-white flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
          <div className="flex items-center gap-2 border-b md:border-b-0 border-slate-200 pb-2 md:pb-0">
            <button
              onClick={() => {
                setActiveTab("orders_payments");
                setStatusFilter("ALL");
                setPage(0);
              }}
              className={`px-4 py-2 text-xs font-bold transition-all cursor-pointer border-b-2 ${
                activeTab === "orders_payments"
                  ? "border-[#0C5ADB] text-[#0C5ADB]"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Orders ↔ Payments ({opSummary?.total ?? 0})
            </button>
            <button
              onClick={() => {
                setActiveTab("settlements_bank");
                setStatusFilter("ALL");
                setPage(0);
              }}
              className={`px-4 py-2 text-xs font-bold transition-all cursor-pointer border-b-2 ${
                activeTab === "settlements_bank"
                  ? "border-[#0C5ADB] text-[#0C5ADB]"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Settlements ↔ Bank ({sbSummary?.total ?? 0})
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Search Input */}
            <div className="relative min-w-[220px] flex-1 sm:flex-initial">
              <input
                type="text"
                placeholder="Search ID, UTR, Reason…"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(0);
                }}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl pl-9 pr-8 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0C5ADB] focus:ring-1 focus:ring-[#0C5ADB] transition"
              />
              <svg className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-700 text-xs cursor-pointer"
                >
                  ✕
                </button>
              )}
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              className="bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-700 font-medium focus:outline-none focus:border-[#0C5ADB] transition cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="MATCHED">MATCHED</option>
              {activeTab === "orders_payments" ? (
                <>
                  <option value="AMOUNT_MISMATCH">AMOUNT_MISMATCH</option>
                  <option value="PAYMENT_MISSING">PAYMENT_MISSING</option>
                  <option value="ORDER_MISSING">ORDER_MISSING</option>
                  <option value="FAILED_PAYMENT">FAILED_PAYMENT</option>
                  <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
                </>
              ) : (
                <>
                  <option value="MATCHED_WITH_TOLERANCE">MATCHED_WITH_TOLERANCE</option>
                  <option value="PENDING_BANK_CREDIT">PENDING_BANK_CREDIT</option>
                  <option value="MISMATCH">MISMATCH</option>
                  <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
                </>
              )}
            </select>
          </div>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[760px]">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px] sticky top-0 backdrop-blur z-10">
                <th className="py-3.5 px-4">Entity ID</th>
                <th className="py-3.5 px-4">Related Match</th>
                <th className="py-3.5 px-4">Match Hierarchy</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Expected Amount</th>
                <th className="py-3.5 px-4 text-right">Actual Amount</th>
                <th className="py-3.5 px-4 text-right">Difference</th>
                <th className="py-3.5 px-4">Diagnostic Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 font-sans text-sm">
                    No reconciliation records found matching criteria.
                  </td>
                </tr>
              ) : (
                items.map((item) => {
                  const cfg = STATUS_CONFIG[item.status] || {
                    label: item.status,
                    bg: "bg-slate-100",
                    text: "text-slate-700",
                    border: "border-slate-200",
                    dot: "bg-slate-400",
                  };
                  const hasDiff = item.difference !== null && item.difference !== 0;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/80 transition-colors"
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex flex-col">
                          <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
                            {item.entity_type}
                          </span>
                          <span className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight">
                            {item.entity_id}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-700">
                        {item.related_entity_id ? (
                          <span className="text-[#0C5ADB] font-bold font-mono text-xs block truncate max-w-[140px]" title={item.related_entity_id}>
                            {item.related_entity_id}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {item.match_type ? (
                          <div className="flex items-center gap-1.5">
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                              {item.match_type}
                            </span>
                            {item.match_type !== "UNMATCHED" && item.confidence !== null && item.confidence > 0 && (
                              <span className="text-[10px] text-slate-500 font-medium">
                                {item.confidence}%
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-sans">
                        <span
                          className={`inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${cfg.bg} ${cfg.text} ${cfg.border}`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                          {cfg.label}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right text-slate-700 font-medium">
                        {formatPaiseToRupees(item.expected_amount)}
                      </td>
                      <td className="py-3.5 px-4 text-right text-slate-700 font-medium">
                        {formatPaiseToRupees(item.actual_amount)}
                      </td>
                      <td
                        className={`py-3.5 px-4 text-right font-bold ${
                          hasDiff
                            ? item.difference! > 0
                              ? "text-emerald-700"
                              : "text-rose-700"
                            : "text-slate-400"
                        }`}
                      >
                        {item.difference !== null && item.difference !== 0 ? (
                          <span>
                            {item.difference > 0 ? "+" : ""}
                            {formatPaiseToRupees(item.difference)}
                          </span>
                        ) : (
                          "₹0.00"
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-sans text-slate-600 text-xs whitespace-normal min-w-[280px] leading-relaxed">
                        {item.reason || "—"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Toolbar */}
        <div className="p-4 border-t border-slate-200 bg-white flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div>
            Showing <span className="font-mono text-slate-900 font-semibold">{items.length > 0 ? page * pageSize + 1 : 0}</span> to{" "}
            <span className="font-mono text-slate-900 font-semibold">{Math.min((page + 1) * pageSize, totalCount)}</span> of{" "}
            <span className="font-mono text-slate-900 font-semibold">{totalCount}</span> records
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3.5 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition cursor-pointer"
            >
              Previous
            </button>
            <span className="font-mono px-2 text-slate-700 font-semibold">
              Page {page + 1} of {Math.max(1, totalPages)}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-3.5 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition cursor-pointer"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
