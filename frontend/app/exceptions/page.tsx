"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getExceptions,
  getExceptionSummary,
  getExceptionDetail,
  getFinancialCases,
  getFinancialCasesSummary,
  getFinancialCaseDetail,
  updateFinancialCaseStatus,
  runExceptionDetection,
  getEntityAuditTrail,
} from "@/lib/api";
import type {
  ExceptionItem,
  ExceptionSummaryResponse,
  ExceptionDetail,
  FinancialExceptionItem,
  FinancialExceptionsSummary,
  ExceptionDetectionRunResponse,
  AuditEvent,
} from "@/types";
import MoneyLineageGraph from "@/components/lineage/MoneyLineageGraph";
import AICaseExplanationTab from "@/components/ai/AICaseExplanationTab";
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

export default function ExceptionsPage() {
  // Main view tab: "cases" (Investigation Engine) or "raw" (Reconciliation Exceptions)
  const [activeTab, setActiveTab] = useState<"cases" | "raw">("cases");
  // Audit trail for selected case
  const [caseAuditEvents, setCaseAuditEvents] = useState<AuditEvent[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  // ─── Investigation Cases State ─────────────────────────────────────────────
  const [casesSummary, setCasesSummary] = useState<FinancialExceptionsSummary | null>(null);
  const [cases, setCases] = useState<FinancialExceptionItem[]>([]);
  const [totalCases, setTotalCases] = useState(0);
  const [casesLoading, setCasesLoading] = useState(true);
  const [casesError, setCasesError] = useState<string | null>(null);

  // Investigation Filters
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [ownerFilter, setOwnerFilter] = useState("ALL");
  const [caseSearch, setCaseSearch] = useState("");
  const [casePage, setCasePage] = useState(0);
  const casePageSize = 25;

  // Selected Case for Deep-Dive Modal
  const [selectedCase, setSelectedCase] = useState<FinancialExceptionItem | null>(null);
  const [caseModalTab, setCaseModalTab] = useState<"ai_explanation" | "lineage" | "findings" | "resolution" | "audit_trail">("ai_explanation");
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [modalStatus, setModalStatus] = useState<string>("OPEN");
  const [modalAssignee, setModalAssignee] = useState<string>("");
  const [modalNotes, setModalNotes] = useState<string>("");
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [statusUpdateSuccess, setStatusUpdateSuccess] = useState(false);

  // Detection Engine Runner State
  const [runningDetection, setRunningDetection] = useState(false);
  const [detectionResult, setDetectionResult] = useState<ExceptionDetectionRunResponse | null>(null);

  // ─── Raw Reconciliation State ──────────────────────────────────────────────
  const [p1Summary, setP1Summary] = useState<ExceptionSummaryResponse | null>(null);
  const [p1Items, setP1Items] = useState<ExceptionItem[]>([]);
  const [p1Total, setP1Total] = useState(0);
  const [p1Loading, setP1Loading] = useState(false);
  const [p1SeverityFilter, setP1SeverityFilter] = useState("ALL");
  const [p1TypeFilter, setP1TypeFilter] = useState("ALL");
  const [p1Search, setP1Search] = useState("");
  const [p1Page, setP1Page] = useState(0);
  const [selectedP1Exception, setSelectedP1Exception] = useState<ExceptionDetail | null>(null);
  const [p1DetailLoading, setP1DetailLoading] = useState(false);

  // ─── Investigation Data Fetchers ───────────────────────────────────────────
  const fetchCasesSummary = useCallback(async () => {
    try {
      const s = await getFinancialCasesSummary();
      setCasesSummary(s);
    } catch {
      // ignore
    }
  }, []);

  const fetchCases = useCallback(async () => {
    setCasesLoading(true);
    setCasesError(null);
    try {
      const res = await getFinancialCases(
        typeFilter !== "ALL" ? typeFilter : undefined,
        riskFilter !== "ALL" ? riskFilter : undefined,
        statusFilter !== "ALL" ? statusFilter : undefined,
        ownerFilter !== "ALL" ? ownerFilter : undefined,
        caseSearch.trim() || undefined,
        casePageSize,
        casePage * casePageSize
      );
      setCases(res.items);
      setTotalCases(res.total);
    } catch (err: any) {
      setCasesError(err?.message || "Failed to load investigation cases.");
    } finally {
      setCasesLoading(false);
    }
  }, [typeFilter, riskFilter, statusFilter, ownerFilter, caseSearch, casePage]);

  // ─── Raw Recon Data Fetchers ───────────────────────────────────────────────
  const fetchP1Data = useCallback(async () => {
    setP1Loading(true);
    try {
      const [sum, res] = await Promise.all([
        getExceptionSummary(),
        getExceptions(
          p1SeverityFilter,
          p1TypeFilter,
          p1Search.trim() || undefined,
          casePageSize,
          p1Page * casePageSize
        ),
      ]);
      setP1Summary(sum);
      setP1Items(res.items);
      setP1Total(res.total);
    } catch {
      // ignore
    } finally {
      setP1Loading(false);
    }
  }, [p1SeverityFilter, p1TypeFilter, p1Search, p1Page]);

  useEffect(() => {
    if (activeTab === "cases") {
      fetchCasesSummary();
      fetchCases();
    } else {
      fetchP1Data();
    }
  }, [activeTab, fetchCasesSummary, fetchCases, fetchP1Data]);

  // ─── Run Detection Engine ──────────────────────────────────────────────────
  const handleRunDetection = async () => {
    setRunningDetection(true);
    setDetectionResult(null);
    try {
      const res = await runExceptionDetection();
      setDetectionResult(res);
      await Promise.all([fetchCasesSummary(), fetchCases()]);
    } catch (err: any) {
      alert(`Detection failed: ${err?.message || "Unknown error"}`);
    } finally {
      setRunningDetection(false);
    }
  };

  // ─── Open Investigation Modal ──────────────────────────────────────────────
  const handleOpenCase = async (item: FinancialExceptionItem) => {
    setSelectedCase(item);
    setModalStatus(item.status);
    setModalAssignee(item.assignee || "");
    setModalNotes(item.resolution_notes || "");
    setCaseModalTab("ai_explanation");
    try {
      const detail = await getFinancialCaseDetail(item.case_id);
      setSelectedCase(detail);
      setModalStatus(detail.status);
      setModalAssignee(detail.assignee || "");
      setModalNotes(detail.resolution_notes || "");
    } catch {
      // fallback to list item
    }
  };

  // ─── Save Case Status Update ───────────────────────────────────────────────
  const handleSaveStatus = async () => {
    if (!selectedCase) return;
    setStatusUpdating(true);
    try {
      const updated = await updateFinancialCaseStatus(selectedCase.case_id, {
        status: modalStatus,
        assignee: modalAssignee.trim() || undefined,
        resolution_notes: modalNotes.trim() || undefined,
      });
      setSelectedCase(updated);
      setStatusUpdateSuccess(true);
      await Promise.all([fetchCasesSummary(), fetchCases()]);
      setTimeout(() => setStatusUpdateSuccess(false), 3000);
    } catch (err: any) {
      alert(`Failed to update status: ${err?.message || "Unknown error"}`);
    } finally {
      setStatusUpdating(false);
    }
  };

  // ─── Open Raw Reconciliation Modal ─────────────────────────────────────────
  const handleOpenP1Detail = async (exc: ExceptionItem) => {
    setP1DetailLoading(true);
    setSelectedP1Exception(null);
    try {
      const detail = await getExceptionDetail(exc.exception_id);
      setSelectedP1Exception(detail);
    } catch {
      setSelectedP1Exception(exc as any);
    } finally {
      setP1DetailLoading(false);
    }
  };

  // ─── Visual Helpers ────────────────────────────────────────────────────────
  const getRiskBadge = (risk: string) => {
    switch (risk?.toUpperCase()) {
      case "CRITICAL":
        return {
          bg: "bg-rose-50",
          text: "text-rose-800",
          border: "border-rose-200",
          dot: "bg-rose-600 animate-ping",
        };
      case "HIGH":
        return {
          bg: "bg-red-50",
          text: "text-red-800",
          border: "border-red-200",
          dot: "bg-red-500",
        };
      case "MEDIUM":
        return {
          bg: "bg-amber-50",
          text: "text-amber-800",
          border: "border-amber-200",
          dot: "bg-amber-500",
        };
      case "LOW":
      default:
        return {
          bg: "bg-slate-100",
          text: "text-slate-700",
          border: "border-slate-200",
          dot: "bg-slate-400",
        };
    }
  };

  const getOwnerBadge = (owner: string) => {
    switch (owner?.toLowerCase()) {
      case "finance":
        return "bg-blue-50 text-[#0C5ADB] border-blue-200";
      case "operations":
        return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "support":
        return "bg-teal-50 text-teal-800 border-teal-200";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toUpperCase()) {
      case "RESOLVED":
        return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "IN_REVIEW":
        return "bg-blue-50 text-blue-800 border-blue-200";
      case "ASSIGNED":
        return "bg-purple-50 text-purple-800 border-purple-200";
      case "DISMISSED":
        return "bg-slate-100 text-slate-600 border-slate-200";
      case "ESCALATED":
        return "bg-rose-50 text-rose-800 border-rose-200";
      case "OPEN":
      default:
        return "bg-amber-50 text-amber-800 border-amber-200";
    }
  };

  const getTypeFriendlyLabel = (type: string) => {
    switch (type) {
      case "PAID_BUT_UNFULFILLED":
        return { label: "Paid but Unfulfilled", icon: "🚚" };
      case "SETTLEMENT_MISSING_IN_BANK":
        return { label: "Settlement Missing in Bank", icon: "🏦" };
      case "PAYMENT_AMOUNT_MISMATCH":
        return { label: "Payment Amount Mismatch", icon: "⚖️" };
      case "CALCULATION_DISCREPANCY":
        return { label: "Settlement Calc Discrepancy", icon: "📑" };
      case "REFUND_MISSING_IN_LEDGER":
        return { label: "Refund Missing in Ledger", icon: "🧾" };
      case "DUPLICATE_PAYMENT_ATTEMPT":
        return { label: "Duplicate Payment Retry", icon: "🔁" };
      default:
        return { label: type?.replace(/_/g, " "), icon: "⚠️" };
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 bg-[#F8FAFC]">
      {/* ─── Header & Action Toolbar ─────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Exception Intelligence & Audit Workspace
            </h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              Investigation Engine
            </span>
          </div>
          <p className="text-slate-500 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
            Investigate financial discrepancies, unfulfilled orders, missing bank credits, and ledger mismatch cases.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Ask AI Trigger */}
          <button
            onClick={() => setIsAssistantOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-xs bg-white hover:bg-slate-50 text-slate-800 shadow-sm border border-emerald-300 transition-all cursor-pointer"
          >
            <div className="w-4 h-4 text-[#00B574] flex items-center justify-center">
              <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
              </svg>
            </div>
            <span>Ask AI</span>
          </button>

          {/* View Switcher Tabs */}
          <div className="flex items-center gap-1 bg-white p-1 rounded-xl border border-slate-200 shadow-xs">
            <button
              onClick={() => setActiveTab("cases")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === "cases"
                  ? "bg-[#0C5ADB] text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Investigation Cases ({casesSummary?.total_cases ?? "..."})
            </button>
            <button
              onClick={() => setActiveTab("raw")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === "raw"
                  ? "bg-[#0C5ADB] text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Raw Recon Exceptions ({p1Summary?.total_exceptions ?? "..."})
            </button>
          </div>
        </div>
      </div>

      {/* ─── VIEW 1: INVESTIGATION CASES ─────────────────────────────────── */}
      {activeTab === "cases" && (
        <div className="space-y-6 sm:space-y-8">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Total Cases */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Investigation Cases
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
                  {casesSummary?.total_cases ?? 0}
                </span>
                <span className="text-xs text-slate-500">active alerts</span>
              </div>
            </div>

            {/* Critical Risk */}
            <div className="rounded-2xl p-5 bg-rose-50 border border-rose-200 shadow-sm">
              <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider flex items-center gap-1.5 mb-1">
                <span className="w-2 h-2 rounded-full bg-rose-600 animate-ping" />
                Critical Risk
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-extrabold text-rose-700 font-mono tracking-tight">
                  {casesSummary?.critical_count ?? 0}
                </span>
                <span className="text-xs text-rose-600">immediate action</span>
              </div>
            </div>

            {/* High Risk */}
            <div className="rounded-2xl p-5 bg-red-50 border border-red-200 shadow-sm">
              <span className="text-[11px] font-bold text-red-800 uppercase tracking-wider block mb-1">
                High Risk
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-extrabold text-red-700 font-mono tracking-tight">
                  {casesSummary?.high_count ?? 0}
                </span>
                <span className="text-xs text-red-600">require audit</span>
              </div>
            </div>

            {/* Total Value at Risk */}
            <div className="rounded-2xl p-5 bg-amber-50 border border-amber-200 shadow-sm">
              <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider block mb-1">
                Total Value at Risk
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-xl sm:text-2xl font-extrabold text-amber-700 font-mono tracking-tight">
                  {casesSummary?.total_value_at_risk_inr ?? "₹0.00"}
                </span>
              </div>
            </div>

            {/* Owner Breakdown */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Ownership Routing
              </span>
              <div className="flex items-center gap-2 mt-2 text-xs">
                <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-[#0C5ADB] border border-blue-200 font-bold">
                  Finance: {casesSummary?.by_owner?.Finance ?? 0}
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                  Ops: {casesSummary?.by_owner?.Operations ?? 0}
                </span>
              </div>
            </div>
          </div>

          {/* Action Toolbar & Filters */}
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 p-4 sm:p-5 rounded-3xl glass-panel border border-white/[0.08]">
            {/* Filter Controls */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Type Filter */}
              <select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value);
                  setCasePage(0);
                }}
                className="bg-white text-slate-700 border border-slate-200 shadow-xs rounded-xl px-3 py-2 text-xs font-semibold focus:outline-none focus:border-[#0C5ADB] transition cursor-pointer"
              >
                <option value="ALL">All Exception Types</option>
                <option value="PAID_BUT_UNFULFILLED">Paid but Unfulfilled</option>
                <option value="SETTLEMENT_MISSING_IN_BANK">Settlement Missing in Bank</option>
                <option value="PAYMENT_AMOUNT_MISMATCH">Payment Amount Mismatch</option>
                <option value="CALCULATION_DISCREPANCY">Calculation Discrepancy</option>
                <option value="REFUND_MISSING_IN_LEDGER">Refund Missing in Ledger</option>
              </select>

              {/* Risk Filter */}
              <select
                value={riskFilter}
                onChange={(e) => {
                  setRiskFilter(e.target.value);
                  setCasePage(0);
                }}
                className="bg-white text-slate-700 border border-slate-200 shadow-xs rounded-xl px-3 py-2 text-xs font-semibold focus:outline-none focus:border-[#0C5ADB] transition cursor-pointer"
              >
                <option value="ALL">All Risk Levels</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCasePage(0);
                }}
                className="bg-white text-slate-700 border border-slate-200 shadow-xs rounded-xl px-3 py-2 text-xs font-semibold focus:outline-none focus:border-[#0C5ADB] transition cursor-pointer"
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="ASSIGNED">Assigned</option>
                <option value="IN_REVIEW">In Review</option>
                <option value="RESOLVED">Resolved</option>
                <option value="DISMISSED">Dismissed</option>
              </select>

              {/* Owner Filter */}
              <select
                value={ownerFilter}
                onChange={(e) => {
                  setOwnerFilter(e.target.value);
                  setCasePage(0);
                }}
                className="bg-white text-slate-700 border border-slate-200 shadow-xs rounded-xl px-3 py-2 text-xs font-semibold focus:outline-none focus:border-[#0C5ADB] transition cursor-pointer"
              >
                <option value="ALL">All Owners</option>
                <option value="Finance">Finance</option>
                <option value="Operations">Operations</option>
                <option value="Support">Support</option>
              </select>

              {/* Search */}
              <div className="relative flex-1 sm:flex-initial min-w-[200px]">
                <input
                  type="text"
                  placeholder="Search case, order, payment..."
                  value={caseSearch}
                  onChange={(e) => {
                    setCaseSearch(e.target.value);
                    setCasePage(0);
                  }}
                  className="bg-white text-slate-900 placeholder-slate-400 border border-slate-200 shadow-xs rounded-xl pl-9 pr-3 py-2 text-xs font-medium w-full focus:outline-none focus:border-[#0C5ADB] transition"
                />
                <svg className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                </svg>
              </div>
            </div>

            {/* Run Detection Engine Button */}
            <button
              onClick={handleRunDetection}
              disabled={runningDetection}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[#0C5ADB] hover:bg-[#0944A8] text-white rounded-xl text-xs font-bold shadow-sm hover:shadow transition disabled:opacity-50 cursor-pointer shrink-0"
            >
              {runningDetection ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Evaluating Rules...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                  </svg>
                  <span>Run Exception Detection</span>
                </>
              )}
            </button>
          </div>

          {/* Detection Result Banner if just run */}
          {detectionResult && (
            <div className="p-4 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-between gap-4 text-xs animate-fadeIn">
              <div className="flex items-center gap-2.5">
                <span className="text-lg">✅</span>
                <div>
                  <span className="font-bold text-blue-900 block">
                    {detectionResult.message}
                  </span>
                  <p className="text-blue-700 mt-0.5">
                    Detected {detectionResult.total_exceptions} exceptions ({detectionResult.unfulfilled_detected} unfulfilled, {detectionResult.settlement_missing_detected} uncredited settlements). Total Value at Risk: {detectionResult.total_value_at_risk_inr}.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDetectionResult(null)}
                className="text-slate-400 hover:text-slate-700 px-2 py-1 cursor-pointer"
              >
                ✕
              </button>
            </div>
          )}

          {/* Cases Table */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
            {casesLoading ? (
              <div className="p-16 flex flex-col items-center justify-center text-slate-500">
                <div className="w-8 h-8 border-2 border-[#0C5ADB] border-t-transparent rounded-full animate-spin mb-3" />
                <span className="text-xs font-medium">Loading financial investigation cases...</span>
              </div>
            ) : casesError ? (
              <div className="p-12 text-center text-rose-600 text-xs font-medium">
                <div className="text-xl mb-1">⚠️</div>
                {casesError}
              </div>
            ) : cases.length === 0 ? (
              <div className="p-16 text-center text-slate-500">
                <div className="text-2xl mb-2">🎉</div>
                <div className="text-sm font-bold text-slate-900 mb-1">No Exceptions Found</div>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  All transactions meet deterministic verification rules under current filter criteria.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs min-w-[760px]">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/90 text-slate-600 font-bold uppercase tracking-wider text-[11px] sticky top-0 backdrop-blur z-10">
                      <th className="py-3.5 px-4">Case ID</th>
                      <th className="py-3.5 px-4">Exception Type</th>
                      <th className="py-3.5 px-4">Risk Level</th>
                      <th className="py-3.5 px-4">Value at Risk</th>
                      <th className="py-3.5 px-4">Related Entity</th>
                      <th className="py-3.5 px-4">Owner</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {cases.map((c) => {
                      const typeInfo = getTypeFriendlyLabel(c.exception_type);
                      const riskBadge = getRiskBadge(c.risk_level);
                      const ownerBadge = getOwnerBadge(c.suggested_owner);
                      const statusBadge = getStatusBadge(c.status);

                      return (
                        <tr
                          key={c.id}
                          onClick={() => handleOpenCase(c)}
                          className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                        >
                          {/* Case ID */}
                          <td className="py-3.5 px-4 font-mono font-bold text-slate-900 group-hover:text-[#0C5ADB] transition">
                            {c.case_id}
                          </td>

                          {/* Exception Type */}
                          <td className="py-3.5 px-4 font-sans">
                            <div className="flex items-center gap-2">
                              <span>{typeInfo.icon}</span>
                              <span className="font-semibold text-slate-800">
                                {typeInfo.label}
                              </span>
                            </div>
                          </td>

                          {/* Risk Level */}
                          <td className="py-3.5 px-4 font-sans">
                            <span
                              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${riskBadge.bg} ${riskBadge.text} ${riskBadge.border}`}
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${riskBadge.dot}`} />
                              {c.risk_level}
                            </span>
                          </td>

                          {/* Value at Risk */}
                          <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                            {c.value_at_risk_inr}
                          </td>

                          {/* Related Entity */}
                          <td className="py-3.5 px-4 font-mono text-slate-700">
                            {c.related_order_id ? (
                              <span className="bg-slate-100 px-2 py-0.5 rounded-lg border border-slate-200 text-slate-700">
                                {c.related_order_id}
                              </span>
                            ) : c.related_settlement_id ? (
                              <span className="bg-slate-100 px-2 py-0.5 rounded-lg border border-slate-200 text-slate-700">
                                {c.related_settlement_id}
                              </span>
                            ) : c.related_payment_id ? (
                              <span className="bg-slate-100 px-2 py-0.5 rounded-lg border border-slate-200 text-slate-700">
                                {c.related_payment_id}
                              </span>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </td>

                          {/* Suggested Owner */}
                          <td className="py-3.5 px-4 font-sans">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${ownerBadge}`}
                            >
                              {c.suggested_owner}
                            </span>
                          </td>

                          {/* Status */}
                          <td className="py-3.5 px-4 font-sans">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${statusBadge}`}
                            >
                              {c.status}
                            </span>
                          </td>

                          {/* Action Button */}
                          <td className="py-3.5 px-4 text-right font-sans">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenCase(c);
                              }}
                              className="px-3 py-1 rounded-lg text-xs font-bold bg-blue-50 hover:bg-blue-100 text-[#0C5ADB] border border-blue-200 transition cursor-pointer"
                            >
                              Investigate →
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Toolbar */}
            <div className="p-4 border-t border-slate-200 bg-slate-50/80 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600">
              <div>
                Showing <span className="font-mono text-slate-900 font-bold">{cases.length > 0 ? casePage * casePageSize + 1 : 0}</span> to{" "}
                <span className="font-mono text-slate-900 font-bold">{Math.min((casePage + 1) * casePageSize, totalCases)}</span> of{" "}
                <span className="font-mono text-slate-900 font-bold">{totalCases}</span> cases
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCasePage((p) => Math.max(0, p - 1))}
                  disabled={casePage === 0}
                  className="px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 shadow-xs transition cursor-pointer font-medium"
                >
                  Previous
                </button>
                <span className="text-slate-700 px-2 font-mono font-semibold">
                  Page {casePage + 1} of {Math.max(1, Math.ceil(totalCases / casePageSize))}
                </span>
                <button
                  onClick={() => setCasePage((p) => p + 1)}
                  disabled={(casePage + 1) * casePageSize >= totalCases}
                  className="px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 shadow-xs transition cursor-pointer font-medium"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── INVESTIGATION DEEP-DIVE MODAL ───────────────────────────────── */}
      {selectedCase && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5 animate-fadeIn"
          onClick={() => setSelectedCase(null)}
        >
          <div
            className="rounded-2xl border border-slate-200 bg-white max-w-5xl w-full shadow-2xl relative max-h-[92vh] flex flex-col overflow-hidden text-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-4 sm:p-5 border-b border-slate-200 bg-slate-50/80 backdrop-blur-xl flex flex-wrap items-center justify-between gap-4 shrink-0">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="text-lg sm:text-xl font-mono font-extrabold text-slate-900">
                    {selectedCase.case_id}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${getRiskBadge(selectedCase.risk_level).bg} ${getRiskBadge(selectedCase.risk_level).text} ${getRiskBadge(selectedCase.risk_level).border}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${getRiskBadge(selectedCase.risk_level).dot}`} />
                    {selectedCase.risk_level} RISK
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${getOwnerBadge(selectedCase.suggested_owner)}`}
                  >
                    Owner: {selectedCase.suggested_owner}
                  </span>
                </div>
                <p className="text-xs sm:text-sm font-bold text-[#0C5ADB] flex items-center gap-1.5">
                  <span>{getTypeFriendlyLabel(selectedCase.exception_type).icon}</span>
                  <span>{getTypeFriendlyLabel(selectedCase.exception_type).label}</span>
                </p>
              </div>

              {/* Status Selector & Save */}
              <div className="flex items-center gap-2">
                <select
                  value={modalStatus}
                  onChange={(e) => setModalStatus(e.target.value)}
                  className="bg-white text-slate-800 border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-bold focus:outline-none focus:border-[#0C5ADB] shadow-xs cursor-pointer"
                >
                  <option value="OPEN">Status: OPEN</option>
                  <option value="IN_REVIEW">Status: IN_REVIEW</option>
                  <option value="ASSIGNED">Status: ASSIGNED</option>
                  <option value="RESOLVED">Status: RESOLVED</option>
                  <option value="DISMISSED">Status: DISMISSED</option>
                  <option value="ESCALATED">Status: ESCALATED</option>
                </select>

                <button
                  onClick={handleSaveStatus}
                  disabled={statusUpdating}
                  className="px-3.5 py-1.5 bg-[#0C5ADB] hover:bg-[#0944A8] text-white rounded-xl text-xs font-bold shadow-xs transition disabled:opacity-50 cursor-pointer"
                >
                  {statusUpdating ? "Saving..." : "Save Status"}
                </button>

                <button
                  onClick={() => setSelectedCase(null)}
                  className="w-8 h-8 rounded-xl bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-800 flex items-center justify-center transition border border-slate-200 cursor-pointer shadow-xs"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Success notification banner */}
            {statusUpdateSuccess && (
              <div className="mx-4 mt-3 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium animate-fadeIn shrink-0 flex items-center gap-2">
                <span>✓</span>
                <span>Case updated successfully. Status is now {modalStatus}.</span>
              </div>
            )}

            {/* Modal Navigation Tabs */}
            <div className="flex items-center gap-2 border-b border-slate-200 px-4 sm:px-5 pt-3 pb-2 shrink-0 overflow-x-auto bg-slate-50/50">
              <button
                onClick={() => setCaseModalTab("ai_explanation")}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 whitespace-nowrap cursor-pointer ${
                  caseModalTab === "ai_explanation"
                    ? "bg-white text-[#0C5ADB] border border-slate-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                ✨ AI Root-Cause Intelligence
              </button>
              <button
                onClick={() => setCaseModalTab("lineage")}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap cursor-pointer ${
                  caseModalTab === "lineage"
                    ? "bg-white text-[#0C5ADB] border border-slate-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                🗺️ Money Lineage Journey
              </button>
              <button
                onClick={() => setCaseModalTab("findings")}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap cursor-pointer ${
                  caseModalTab === "findings"
                    ? "bg-white text-[#0C5ADB] border border-slate-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                📋 Verified Findings & Evidence
              </button>
              <button
                onClick={() => setCaseModalTab("resolution")}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap cursor-pointer ${
                  caseModalTab === "resolution"
                    ? "bg-white text-[#0C5ADB] border border-slate-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                ⚖️ Audit & Resolution
              </button>
              <button
                onClick={async () => {
                  setCaseModalTab("audit_trail");
                  if (selectedCase) {
                    setAuditLoading(true);
                    try {
                      const res = await getEntityAuditTrail(selectedCase.case_id, "EXCEPTION_CASE");
                      setCaseAuditEvents(res.items);
                    } catch { setCaseAuditEvents([]); }
                    finally { setAuditLoading(false); }
                  }
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap cursor-pointer ${
                  caseModalTab === "audit_trail"
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                📋 Audit Trail
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
              {/* TAB 0: AI ROOT-CAUSE INTELLIGENCE */}
              {caseModalTab === "ai_explanation" && (
                <AICaseExplanationTab
                  caseId={selectedCase.case_id}
                  onApplyAction={(actionText) => {
                    setModalNotes((prev) => (prev ? `${prev}\n- ${actionText}` : `- ${actionText}`));
                    setCaseModalTab("resolution");
                  }}
                />
              )}

              {/* TAB 1: MONEY LINEAGE GRAPH */}
              {caseModalTab === "lineage" && (
                <div className="space-y-3">
                  <div className="text-xs text-slate-500">
                    Interactive multi-system journey. Click any node to inspect source attributes, deterministic rules, and confidence metrics.
                  </div>
                  <MoneyLineageGraph
                    entityType={
                      selectedCase.related_order_id
                        ? "order"
                        : selectedCase.related_settlement_id
                        ? "settlement"
                        : selectedCase.related_payment_id
                        ? "payment"
                        : "order"
                    }
                    entityId={
                      selectedCase.related_order_id ||
                      selectedCase.related_settlement_id ||
                      selectedCase.related_payment_id ||
                      selectedCase.case_id
                    }
                    className="h-[460px] rounded-2xl overflow-hidden border border-slate-200"
                  />
                </div>
              )}

              {/* TAB 2: FINDINGS & EVIDENCE */}
              {caseModalTab === "findings" && (
                <div className="space-y-4">
                  {/* Financial Summary KPIs */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block mb-1">
                        Value at Risk
                      </span>
                      <span className="text-xl font-bold text-rose-600 font-mono">
                        {selectedCase.value_at_risk_inr}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block mb-1">
                        Triggering Date
                      </span>
                      <span className="text-xs font-mono font-medium text-slate-800">
                        {selectedCase.detected_at?.split(".")[0] || "N/A"}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block mb-1">
                        Assigned Owner
                      </span>
                      <span className="text-xs font-bold text-[#0C5ADB]">
                        {selectedCase.suggested_owner} Team
                      </span>
                    </div>
                  </div>

                  {/* Verified Explanation */}
                  <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs leading-relaxed">
                    <div className="font-bold text-amber-900 mb-1.5 flex items-center gap-1.5">
                      <span>💡 Verified Financial Finding:</span>
                    </div>
                    <p className="text-slate-800 leading-relaxed font-normal">
                      {selectedCase.explanation}
                    </p>
                  </div>

                  {/* Triggering Deterministic Rule */}
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                    <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-1">
                      Deterministic Engine Trigger Rule
                    </div>
                    <p className="font-mono text-blue-900 bg-blue-50/70 p-3 rounded-xl border border-blue-200 leading-relaxed font-semibold">
                      {selectedCase.triggering_rule}
                    </p>
                  </div>

                  {/* Structured Evidence Table */}
                  {selectedCase.evidence && Object.keys(selectedCase.evidence).length > 0 && (
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                      <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-3">
                        Structured Evidence Dossier
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {Object.entries(selectedCase.evidence).map(([k, v]) => (
                          <div
                            key={k}
                            className="p-2.5 rounded-xl bg-white border border-slate-200 flex items-center justify-between gap-2 shadow-2xs"
                          >
                            <span className="text-slate-500 font-medium text-[11px] truncate">{k}</span>
                            <span className="font-mono font-bold text-slate-900 text-[11px] truncate max-w-[180px]">
                              {String(v)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: RESOLUTION & AUDIT */}
              {caseModalTab === "resolution" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-bold text-slate-700 block mb-1.5">
                        Assignee
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Priya Roy (Finance Lead)"
                        value={modalAssignee}
                        onChange={(e) => setModalAssignee(e.target.value)}
                        className="w-full bg-white text-slate-900 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs focus:outline-none focus:border-[#0C5ADB] shadow-xs"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-bold text-slate-700 block mb-1.5">
                        Case Status
                      </label>
                      <select
                        value={modalStatus}
                        onChange={(e) => setModalStatus(e.target.value)}
                        className="w-full bg-white text-slate-900 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs font-semibold focus:outline-none focus:border-[#0C5ADB] cursor-pointer shadow-xs"
                      >
                        <option value="OPEN">OPEN</option>
                        <option value="ASSIGNED">ASSIGNED</option>
                        <option value="IN_REVIEW">IN_REVIEW</option>
                        <option value="RESOLVED">RESOLVED</option>
                        <option value="DISMISSED">DISMISSED</option>
                        <option value="ESCALATED">ESCALATED</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-700 block mb-1.5">
                      Resolution Notes & Audit Comments
                    </label>
                    <textarea
                      rows={4}
                      placeholder="Add investigation actions taken, vendor ticket IDs, refund approval reference..."
                      value={modalNotes}
                      onChange={(e) => setModalNotes(e.target.value)}
                      className="w-full bg-white text-slate-900 border border-slate-300 rounded-xl p-3.5 text-xs focus:outline-none focus:border-[#0C5ADB] leading-relaxed shadow-xs"
                    />
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={handleSaveStatus}
                      disabled={statusUpdating}
                      className="px-5 py-2.5 bg-[#0C5ADB] hover:bg-[#0944A8] text-white rounded-xl text-xs font-bold shadow-xs transition disabled:opacity-50 cursor-pointer"
                    >
                      {statusUpdating ? "Saving..." : "Save Case Audit"}
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 4: AUDIT TRAIL */}
              {caseModalTab === "audit_trail" && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 p-3 rounded-xl font-medium">
                    <span>🔒</span>
                    <span>Immutable audit log. Events are cryptographically chained and never modified.</span>
                  </div>
                  {auditLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="h-14 rounded-xl bg-slate-100 border border-slate-200 animate-pulse" />
                      ))}
                    </div>
                  ) : caseAuditEvents.length === 0 ? (
                    <div className="text-center py-10 text-slate-500">
                      <div className="text-2xl mb-2">📋</div>
                      <p className="text-sm font-bold text-slate-800 mb-1">No audit events yet</p>
                      <p className="text-xs text-slate-500">Events will appear when the case status is changed.</p>
                    </div>
                  ) : (
                    <div className="space-y-2.5">
                      {caseAuditEvents.map((event) => {
                        const eventColors: Record<string, string> = {
                          DETECTION: "border-l-blue-500 bg-blue-50/50",
                          STATUS_CHANGE: "border-l-indigo-500 bg-indigo-50/50",
                          ASSIGNMENT: "border-l-violet-500 bg-violet-50/50",
                          NOTE_ADDED: "border-l-amber-500 bg-amber-50/50",
                          RESOLUTION: "border-l-emerald-500 bg-emerald-50/50",
                          ESCALATION: "border-l-rose-500 bg-rose-50/50",
                          ENGINE_RUN: "border-l-slate-400 bg-slate-50/70",
                        };
                        const colorCls = eventColors[event.event_type] ?? "border-l-slate-400 bg-slate-50/70";
                        return (
                          <div
                            key={event.event_id}
                            className={`border-l-3 rounded-r-xl p-3.5 border border-slate-200 ${colorCls}`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-bold text-slate-800 bg-white border border-slate-200 px-2 py-0.5 rounded-md">
                                  {event.event_type.replace(/_/g, " ")}
                                </span>
                                <span className="text-[10px] text-slate-500 font-medium">by {event.actor}</span>
                              </div>
                              <span className="text-[10px] text-slate-500 font-mono">
                                {event.created_at ? new Date(event.created_at).toLocaleString("en-IN") : ""}
                              </span>
                            </div>
                            {(event.from_value || event.to_value) && (
                              <div className="flex items-center gap-2 text-[11px] mt-1 font-mono">
                                {event.from_value && (
                                  <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                                    {JSON.stringify(event.from_value)}
                                  </span>
                                )}
                                {event.from_value && event.to_value && (
                                  <span className="text-slate-400">→</span>
                                )}
                                {event.to_value && (
                                  <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-900 font-bold">
                                    {JSON.stringify(event.to_value)}
                                  </span>
                                )}
                              </div>
                            )}
                            {event.notes && (
                              <p className="text-[11px] text-slate-700 mt-1 italic leading-relaxed">{event.notes}</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500 shrink-0">
              <span className="font-mono text-[11px]">
                Detected: {selectedCase.detected_at?.split(".")[0] || "N/A"}
              </span>
              <button
                onClick={() => setSelectedCase(null)}
                className="px-4 py-2 rounded-xl bg-white hover:bg-slate-100 text-slate-700 font-bold border border-slate-200 shadow-2xs transition cursor-pointer"
              >
                Close Investigation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── VIEW 2: RAW RECONCILIATION EXCEPTIONS ──────────────────────── */}
      {activeTab === "raw" && (
        <div className="space-y-6 sm:space-y-8">
          {/* Raw Recon Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Total Recon Exceptions</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
                {p1Summary?.total_exceptions ?? 0}
              </span>
            </div>
            <div className="rounded-2xl p-5 bg-rose-50/60 border border-rose-200 shadow-xs">
              <span className="text-xs font-bold text-rose-700 uppercase tracking-wider block mb-1">High Severity</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-rose-700 font-mono tracking-tight">
                {p1Summary?.high_severity ?? 0}
              </span>
            </div>
            <div className="rounded-2xl p-5 bg-amber-50/60 border border-amber-200 shadow-xs">
              <span className="text-xs font-bold text-amber-800 uppercase tracking-wider block mb-1">Medium Severity</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-amber-700 font-mono tracking-tight">
                {p1Summary?.medium_severity ?? 0}
              </span>
            </div>
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Value at Risk</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
                {formatPaiseToRupees(p1Summary?.total_value_at_risk)}
              </span>
            </div>
          </div>

          {/* Raw Recon Filter Bar */}
          <div className="flex flex-wrap items-center gap-3 p-4 sm:p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <select
              value={p1SeverityFilter}
              onChange={(e) => {
                setP1SeverityFilter(e.target.value);
                setP1Page(0);
              }}
              className="bg-white text-slate-700 border border-slate-200 shadow-2xs rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer"
            >
              <option value="ALL">All Severities</option>
              <option value="HIGH">High Severity</option>
              <option value="MEDIUM">Medium Severity</option>
              <option value="LOW">Low Severity</option>
            </select>

            <select
              value={p1TypeFilter}
              onChange={(e) => {
                setP1TypeFilter(e.target.value);
                setP1Page(0);
              }}
              className="bg-white text-slate-700 border border-slate-200 shadow-2xs rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer"
            >
              <option value="ALL">All Types</option>
              <option value="PAYMENT_MISSING">Payment Missing</option>
              <option value="ORDER_MISSING">Order Missing</option>
              <option value="AMOUNT_MISMATCH">Amount Mismatch</option>
              <option value="FAILED_PAYMENT">Failed Payment</option>
              <option value="AMBIGUOUS_PAYMENT">Ambiguous Payment</option>
              <option value="SETTLEMENT_MISSING_IN_BANK">Settlement Missing in Bank</option>
              <option value="SETTLEMENT_AMOUNT_MISMATCH">Settlement Amount Mismatch</option>
            </select>

            <div className="relative flex-1 sm:flex-initial min-w-[200px]">
              <input
                type="text"
                placeholder="Search ID, reason..."
                value={p1Search}
                onChange={(e) => {
                  setP1Search(e.target.value);
                  setP1Page(0);
                }}
                className="bg-white text-slate-900 placeholder-slate-400 border border-slate-200 shadow-2xs rounded-xl pl-9 pr-3 py-2 text-xs font-medium w-full focus:outline-none focus:border-[#0C5ADB]"
              />
              <svg className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
            </div>
          </div>

          {/* Raw Recon Table */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
            {p1Loading ? (
              <div className="p-12 text-center text-slate-500 text-xs font-medium">Loading exceptions...</div>
            ) : p1Items.length === 0 ? (
              <div className="p-12 text-center text-slate-500 text-xs font-medium">No records found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs min-w-[760px]">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/90 text-slate-600 uppercase tracking-wider text-[11px] sticky top-0 backdrop-blur z-10 font-bold">
                      <th className="py-3.5 px-4">Exception ID</th>
                      <th className="py-3.5 px-4">Type</th>
                      <th className="py-3.5 px-4">Entity</th>
                      <th className="py-3.5 px-4">Severity</th>
                      <th className="py-3.5 px-4">Amount at Risk</th>
                      <th className="py-3.5 px-4">Diagnostic Finding</th>
                      <th className="py-3.5 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {p1Items.map((item) => (
                      <tr
                        key={item.id}
                        onClick={() => handleOpenP1Detail(item)}
                        className="hover:bg-slate-50/80 transition cursor-pointer"
                      >
                        <td className="py-3.5 px-4 font-mono font-bold text-slate-900">{item.exception_id}</td>
                        <td className="py-3.5 px-4 text-slate-800 font-sans font-medium">{item.exception_type}</td>
                        <td className="py-3.5 px-4 font-mono text-slate-600">
                          {item.entity_type} {item.entity_id}
                        </td>
                        <td className="py-3.5 px-4 font-sans">
                          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${getRiskBadge(item.severity).bg} ${getRiskBadge(item.severity).text} ${getRiskBadge(item.severity).border}`}>
                            {item.severity}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                          {formatPaiseToRupees(item.amount_at_risk)}
                        </td>
                        <td className="py-3.5 px-4 text-slate-500 font-sans truncate max-w-xs">{item.reason}</td>
                        <td className="py-3.5 px-4 text-right font-sans">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenP1Detail(item);
                            }}
                            className="px-3 py-1 text-xs font-bold rounded-lg bg-blue-50 text-[#0C5ADB] hover:bg-blue-100 border border-blue-200 transition cursor-pointer"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Raw Recon Detail Modal */}
      {selectedP1Exception && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setSelectedP1Exception(null)}
        >
          <div
            className="rounded-2xl border border-slate-200 bg-white p-6 max-w-2xl w-full shadow-2xl relative max-h-[90vh] overflow-y-auto text-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between pb-4 border-b border-slate-200 mb-6">
              <div>
                <span className="text-xl font-bold text-slate-900 font-mono">
                  {selectedP1Exception.exception_id}
                </span>
                <p className="text-sm font-semibold text-[#0C5ADB] mt-1">
                  {selectedP1Exception.exception_type}
                </p>
              </div>
              <button
                onClick={() => setSelectedP1Exception(null)}
                className="w-8 h-8 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 flex items-center justify-center transition border border-slate-200 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block">Expected Amount</span>
                <span className="text-sm font-bold text-slate-900 font-mono mt-1 block">
                  {formatPaiseToRupees(selectedP1Exception.expected_amount)}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block">Actual Captured</span>
                <span className="text-sm font-bold text-slate-900 font-mono mt-1 block">
                  {formatPaiseToRupees(selectedP1Exception.actual_amount)}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200">
                <span className="text-[10px] text-rose-700 uppercase font-bold tracking-wider block">Amount at Risk</span>
                <span className="text-sm font-bold text-rose-700 font-mono mt-1 block">
                  {formatPaiseToRupees(selectedP1Exception.amount_at_risk)}
                </span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs leading-relaxed mb-6">
              <div className="font-bold text-amber-900 mb-1">Finding:</div>
              <p className="text-slate-800">{selectedP1Exception.reason}</p>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setSelectedP1Exception(null)}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 transition cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Financial Assistant Sliding Drawer */}
      <FinancialAssistantDrawer
        isOpen={isAssistantOpen}
        onClose={() => setIsAssistantOpen(false)}
      />
    </div>
  );
}
