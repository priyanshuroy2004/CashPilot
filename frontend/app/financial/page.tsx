"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");


// ─── Types ───────────────────────────────────────────────────────────────────

interface SettlementCalcSummary {
  total: number;
  correct: number;
  discrepancy: number;
}

interface TaxReconSummary {
  total_checks: number;
  settlements_checked: number;
  by_status: Record<string, number>;
}

interface RefundReconSummary {
  total_refunds: number;
  by_status: Record<string, number>;
}

interface FinancialSummary {
  settlement_calculations: SettlementCalcSummary;
  tax_reconciliation: TaxReconSummary;
  refund_reconciliation: RefundReconSummary;
}

interface SettlementCalcRow {
  settlement_id: string;
  gross_amount_inr: number;
  fee_amount_inr: number;
  tax_amount_inr: number;
  refund_adjustment: number;
  expected_net_inr: number;
  reported_net_inr: number;
  difference_inr: number;
  calculation_status: string;
  payment_count: number;
}

interface TaxReconRow {
  id: number;
  settlement_id: string;
  component: string;
  expected_amount_inr: number;
  ledger_amount_inr: number | null;
  difference_inr: number | null;
  status: string;
  ledger_entry_id: string | null;
  notes: string | null;
}

interface RefundReconRow {
  id: number;
  refund_id: string;
  payment_id: string | null;
  settlement_id: string | null;
  refund_amount_inr: number;
  ledger_amount_inr: number | null;
  difference_inr: number | null;
  refund_status: string;
  duplicate_count: number;
  notes: string | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function inr(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(v);
}

function StatusPill({ status }: { status: string }) {
  const s = status.toUpperCase();

  const map: Record<string, { cls: string; dot: string }> = {
    CORRECT: { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500" },
    DISCREPANCY: { cls: "bg-rose-50 text-rose-800 border-rose-200", dot: "bg-rose-500 animate-pulse" },
    MATCHED: { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500" },
    MISSING_LEDGER_ENTRY: { cls: "bg-amber-50 text-amber-900 border-amber-200", dot: "bg-amber-500" },
    AMOUNT_MISMATCH: { cls: "bg-rose-50 text-rose-800 border-rose-200", dot: "bg-rose-500" },
    DUPLICATE_ENTRY: { cls: "bg-orange-50 text-orange-900 border-orange-200", dot: "bg-orange-500" },
    REFUND_MATCHED: { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500" },
    REFUND_MISSING_IN_LEDGER: { cls: "bg-amber-50 text-amber-900 border-amber-200", dot: "bg-amber-500" },
    REFUND_AMOUNT_MISMATCH: { cls: "bg-rose-50 text-rose-800 border-rose-200", dot: "bg-rose-500" },
    DUPLICATE_REFUND: { cls: "bg-orange-50 text-orange-900 border-orange-200", dot: "bg-orange-500" },
    REFUND_PENDING: { cls: "bg-blue-50 text-[#0C5ADB] border-blue-200", dot: "bg-[#0C5ADB]" },
    REFUND_SETTLEMENT_ADJUSTMENT_MISSING: { cls: "bg-purple-50 text-purple-900 border-purple-200", dot: "bg-purple-500" },
    PENDING_REVIEW: { cls: "bg-yellow-50 text-yellow-900 border-yellow-200", dot: "bg-yellow-500" },
  };

  const item = map[s] ?? { cls: "bg-slate-100 text-slate-700 border-slate-200", dot: "bg-slate-400" };
  const label = s.replace(/_/g, " ");
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${item.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${item.dot}`} />
      {label}
    </span>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SummaryCard({
  title,
  icon,
  mainValue,
  mainLabel,
  subItems,
  accentColor,
}: {
  title: string;
  icon: React.ReactNode;
  mainValue: number;
  mainLabel: string;
  subItems: { label: string; value: number; color: string }[];
  accentColor: string;
}) {
  return (
    <div className="bg-white rounded-2xl p-5 sm:p-6 relative overflow-hidden border border-slate-200 shadow-xs hover:shadow transition-all duration-200">
      <div className={`absolute top-0 inset-x-0 h-1 ${accentColor}`} />
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-[11px] text-slate-500 font-bold uppercase tracking-wider mb-1">{title}</p>
          <p className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{mainValue}</p>
          <p className="text-xs text-slate-500 mt-0.5">{mainLabel}</p>
        </div>
        <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center shrink-0">
          {icon}
        </div>
      </div>
      <div className="space-y-2 border-t border-slate-100 pt-3">
        {subItems.map((item) => (
          <div key={item.label} className="flex items-center justify-between text-xs">
            <span className="text-slate-500">{item.label}</span>
            <span className={`font-bold font-mono ${item.color}`}>{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type TabId = "calculations" | "tax" | "refunds";

export default function FinancialPage() {
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("calculations");
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Table data
  const [calcRows, setCalcRows] = useState<SettlementCalcRow[]>([]);
  const [taxRows, setTaxRows] = useState<TaxReconRow[]>([]);
  const [refundRows, setRefundRows] = useState<RefundReconRow[]>([]);
  const [tableLoading, setTableLoading] = useState(false);

  // Filters
  const [calcFilter, setCalcFilter] = useState("");
  const [taxFilter, setTaxFilter] = useState("");
  const [refundFilter, setRefundFilter] = useState("");

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/financial/summary`);
      if (!res.ok) throw new Error(await res.text());
      setSummary(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTableData = useCallback(async () => {
    setTableLoading(true);
    try {
      const [calcRes, taxRes, refundRes] = await Promise.all([
        fetch(`${API_BASE}/api/financial/settlement-calculations?limit=200`),
        fetch(`${API_BASE}/api/financial/tax-reconciliation?limit=500`),
        fetch(`${API_BASE}/api/financial/refund-reconciliation?limit=200`),
      ]);
      if (calcRes.ok) setCalcRows((await calcRes.json()).items ?? []);
      if (taxRes.ok) setTaxRows((await taxRes.json()).items ?? []);
      if (refundRes.ok) setRefundRows((await refundRes.json()).items ?? []);
    } finally {
      setTableLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
    fetchTableData();
  }, [fetchSummary, fetchTableData]);

  const handleRun = async () => {
    setRunning(true);
    setRunResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/financial/run`, { method: "POST" });
      const data = await res.json();
      if (res.ok && data.success) {
        setRunResult(`Success — ${data.settlement_calculations.total} settlements calculated, ${data.refund_reconciliation.total_refunds} refunds matched.`);
        await Promise.all([fetchSummary(), fetchTableData()]);
      } else {
        setRunResult(`Error: ${data.detail || "Unknown error"}`);
      }
    } catch (e: unknown) {
      setRunResult(`Network error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setRunning(false);
    }
  };

  // Filtered rows
  const filteredCalc = calcRows.filter((r) =>
    calcFilter ? r.settlement_id.toLowerCase().includes(calcFilter.toLowerCase()) || r.calculation_status.toLowerCase().includes(calcFilter.toLowerCase()) : true
  );
  const filteredTax = taxRows.filter((r) =>
    taxFilter ? r.settlement_id.toLowerCase().includes(taxFilter.toLowerCase()) || r.component.toLowerCase().includes(taxFilter.toLowerCase()) || r.status.toLowerCase().includes(taxFilter.toLowerCase()) : true
  );
  const filteredRefund = refundRows.filter((r) =>
    refundFilter ? r.refund_id.toLowerCase().includes(refundFilter.toLowerCase()) || r.refund_status.toLowerCase().includes(refundFilter.toLowerCase()) : true
  );

  const tabs: { id: TabId; label: string; count: number }[] = [
    { id: "calculations", label: "Settlement Calculations", count: calcRows.length },
    { id: "tax", label: "Tax Line Matching", count: taxRows.length },
    { id: "refunds", label: "Refund Reconciliation", count: refundRows.length },
  ];

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8">
      {/* ─── Header & Action Toolbar ─────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Financial Intelligence
            </h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-[#0C5ADB] border border-blue-200">
              <span className="w-2 h-2 rounded-full bg-[#0C5ADB] animate-pulse" />
              Intelligence Engine
            </span>
          </div>
          <p className="text-slate-500 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
            Fee/tax/net calculation verification · Tax-line ledger matching · Multi-point refund reconciliation.
          </p>
        </div>

        <button
          id="run-financial-engines-btn"
          onClick={handleRun}
          disabled={running}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#0C5ADB] hover:bg-[#0944A8] disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer self-start md:self-auto shrink-0"
        >
          {running ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>Running Engines…</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Run All Engines</span>
            </>
          )}
        </button>
      </div>

      {/* Run result banner */}
      {runResult && (
        <div className={`p-4 rounded-2xl text-xs sm:text-sm font-medium border flex items-center gap-2.5 animate-fadeIn ${
          runResult.startsWith("Success")
            ? "bg-emerald-50 text-emerald-800 border-emerald-200 shadow-xs"
            : "bg-rose-50 text-rose-800 border-rose-200 shadow-xs"
        }`}>
          <span>{runResult.startsWith("Success") ? "✓" : "⚠️"}</span>
          <span>{runResult}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 text-rose-800 border border-rose-200 text-xs sm:text-sm flex items-center gap-2.5">
          <span>⚠️</span>
          <span>{error} — Run demo load + reconciliation first, then click &quot;Run All Engines&quot;.</span>
        </div>
      )}

      {/* ─── Summary Cards ───────────────────────────────────────────────── */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-white rounded-2xl h-40 animate-pulse border border-slate-200" />
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SummaryCard
            title="Settlement Calculations"
            icon={<svg className="w-5 h-5 text-[#0C5ADB]" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>}
            mainValue={summary.settlement_calculations.total}
            mainLabel="settlements verified"
            subItems={[
              { label: "Correct", value: summary.settlement_calculations.correct, color: "text-emerald-600" },
              { label: "Discrepancy", value: summary.settlement_calculations.discrepancy, color: "text-rose-600" },
            ]}
            accentColor="bg-[#0C5ADB]"
          />
          <SummaryCard
            title="Tax Line Matching"
            icon={<svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" /></svg>}
            mainValue={summary.tax_reconciliation.total_checks}
            mainLabel="component checks"
            subItems={[
              { label: "Matched", value: summary.tax_reconciliation.by_status["MATCHED"] ?? 0, color: "text-emerald-600" },
              { label: "Missing Ledger Entry", value: summary.tax_reconciliation.by_status["MISSING_LEDGER_ENTRY"] ?? 0, color: "text-amber-700" },
              { label: "Amount Mismatch", value: summary.tax_reconciliation.by_status["AMOUNT_MISMATCH"] ?? 0, color: "text-rose-600" },
              { label: "Duplicate Entry", value: summary.tax_reconciliation.by_status["DUPLICATE_ENTRY"] ?? 0, color: "text-orange-700" },
            ]}
            accentColor="bg-amber-500"
          />
          <SummaryCard
            title="Refund Reconciliation"
            icon={<svg className="w-5 h-5 text-[#00B574]" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>}
            mainValue={summary.refund_reconciliation.total_refunds}
            mainLabel="refunds processed"
            subItems={[
              { label: "Matched", value: summary.refund_reconciliation.by_status["REFUND_MATCHED"] ?? 0, color: "text-emerald-600" },
              { label: "Missing in Ledger", value: summary.refund_reconciliation.by_status["REFUND_MISSING_IN_LEDGER"] ?? 0, color: "text-amber-700" },
              { label: "Amount Mismatch", value: summary.refund_reconciliation.by_status["REFUND_AMOUNT_MISMATCH"] ?? 0, color: "text-rose-600" },
              { label: "Duplicate", value: summary.refund_reconciliation.by_status["DUPLICATE_REFUND"] ?? 0, color: "text-orange-700" },
              { label: "Pending", value: summary.refund_reconciliation.by_status["REFUND_PENDING"] ?? 0, color: "text-blue-600" },
            ]}
            accentColor="bg-[#00B574]"
          />
        </div>
      ) : null}

      {/* ─── Tabs & Data Tables ──────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="flex border-b border-slate-200 p-2 bg-slate-50/80 overflow-x-auto gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              id={`financial-tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-white text-[#0C5ADB] border border-slate-200 shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <span>{tab.label}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold font-mono ${
                activeTab === tab.id ? "bg-blue-50 text-[#0C5ADB]" : "bg-slate-100 text-slate-600"
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {tableLoading ? (
          <div className="flex items-center justify-center h-48">
            <div className="flex items-center gap-2 text-slate-500 text-xs">
              <div className="w-5 h-5 border-2 border-[#0C5ADB] border-t-transparent rounded-full animate-spin" />
              <span>Loading financial records…</span>
            </div>
          </div>
        ) : (
          <>
            {/* Settlement Calculations Tab */}
            {activeTab === "calculations" && (
              <div>
                <div className="p-4 border-b border-slate-200 flex items-center gap-3">
                  <div className="relative flex-1">
                    <input
                      id="calc-search"
                      type="text"
                      placeholder="Search settlement ID or status…"
                      value={calcFilter}
                      onChange={(e) => setCalcFilter(e.target.value)}
                      className="w-full bg-white border border-slate-200 shadow-2xs rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0C5ADB] transition"
                    />
                    <svg className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                    </svg>
                  </div>
                  <span className="text-xs text-slate-500 font-mono font-semibold">{filteredCalc.length} rows</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs min-w-[760px]">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/90 text-slate-600 uppercase tracking-wider text-[11px] sticky top-0 backdrop-blur z-10 font-bold">
                        <th className="px-4 py-3.5 text-left">Settlement ID</th>
                        <th className="px-4 py-3.5 text-right">Gross</th>
                        <th className="px-4 py-3.5 text-right">Fee</th>
                        <th className="px-4 py-3.5 text-right">GST</th>
                        <th className="px-4 py-3.5 text-right">Expected Net</th>
                        <th className="px-4 py-3.5 text-right">Reported Net</th>
                        <th className="px-4 py-3.5 text-right">Difference</th>
                        <th className="px-4 py-3.5 text-center">Status</th>
                        <th className="px-4 py-3.5 text-center">Payments</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      {filteredCalc.length === 0 ? (
                        <tr>
                          <td colSpan={9} className="px-4 py-12 text-center text-slate-500 font-sans text-xs">
                            No records found. Run engines or adjust search query.
                          </td>
                        </tr>
                      ) : (
                        filteredCalc.map((row) => (
                          <tr key={row.settlement_id} className="hover:bg-slate-50/80 transition-colors">
                            <td className="px-4 py-3 font-mono text-xs text-slate-900 font-bold">{row.settlement_id}</td>
                            <td className="px-4 py-3 text-right text-slate-600 tabular-nums">{inr(row.gross_amount_inr)}</td>
                            <td className="px-4 py-3 text-right text-slate-600 tabular-nums">{inr(row.fee_amount_inr)}</td>
                            <td className="px-4 py-3 text-right text-slate-600 tabular-nums">{inr(row.tax_amount_inr)}</td>
                            <td className="px-4 py-3 text-right text-emerald-700 font-bold tabular-nums">{inr(row.expected_net_inr)}</td>
                            <td className="px-4 py-3 text-right text-slate-800 tabular-nums">{inr(row.reported_net_inr)}</td>
                            <td className={`px-4 py-3 text-right font-bold tabular-nums ${row.difference_inr && Math.abs(row.difference_inr) > 0.01 ? "text-rose-600" : "text-slate-400"}`}>
                              {row.difference_inr !== 0 ? inr(row.difference_inr) : "—"}
                            </td>
                            <td className="px-4 py-3 text-center font-sans">
                              <StatusPill status={row.calculation_status} />
                            </td>
                            <td className="px-4 py-3 text-center text-slate-700 text-xs font-mono">{row.payment_count}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tax Reconciliation Tab */}
            {activeTab === "tax" && (
              <div>
                <div className="p-4 border-b border-slate-200 flex items-center gap-3">
                  <div className="relative flex-1">
                    <input
                      id="tax-search"
                      type="text"
                      placeholder="Search settlement ID, component, or status…"
                      value={taxFilter}
                      onChange={(e) => setTaxFilter(e.target.value)}
                      className="w-full bg-white border border-slate-200 shadow-2xs rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0C5ADB] transition"
                    />
                    <svg className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                    </svg>
                  </div>
                  <span className="text-xs text-slate-500 font-mono font-semibold">{filteredTax.length} rows</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs min-w-[760px]">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/90 text-slate-600 uppercase tracking-wider text-[11px] sticky top-0 backdrop-blur z-10 font-bold">
                        <th className="px-4 py-3.5 text-left">Settlement ID</th>
                        <th className="px-4 py-3.5 text-left">Component</th>
                        <th className="px-4 py-3.5 text-right">Expected</th>
                        <th className="px-4 py-3.5 text-right">Ledger</th>
                        <th className="px-4 py-3.5 text-right">Difference</th>
                        <th className="px-4 py-3.5 text-center">Status</th>
                        <th className="px-4 py-3.5 text-left">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      {filteredTax.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="px-4 py-12 text-center text-slate-500 font-sans text-xs">
                            No records found. Run engines first.
                          </td>
                        </tr>
                      ) : (
                        filteredTax.map((row) => (
                          <tr key={row.id} className="hover:bg-slate-50/80 transition-colors">
                            <td className="px-4 py-3 font-mono text-xs text-slate-900 font-bold">{row.settlement_id}</td>
                            <td className="px-4 py-3">
                              <span className="text-xs font-bold text-slate-800 bg-slate-100 px-2.5 py-0.5 rounded-lg border border-slate-200">{row.component}</span>
                            </td>
                            <td className="px-4 py-3 text-right text-slate-700 tabular-nums">{inr(row.expected_amount_inr)}</td>
                            <td className="px-4 py-3 text-right text-slate-800 tabular-nums">{row.ledger_amount_inr !== null ? inr(row.ledger_amount_inr) : "—"}</td>
                            <td className={`px-4 py-3 text-right font-bold tabular-nums ${row.difference_inr && Math.abs(row.difference_inr) > 0.01 ? "text-rose-600" : "text-slate-400"}`}>
                              {row.difference_inr !== null && row.difference_inr !== 0 ? inr(row.difference_inr) : "—"}
                            </td>
                            <td className="px-4 py-3 text-center font-sans">
                              <StatusPill status={row.status} />
                            </td>
                            <td className="px-4 py-3 text-xs text-slate-500 max-w-xs truncate font-sans" title={row.notes ?? ""}>
                              {row.notes ?? "—"}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Refund Reconciliation Tab */}
            {activeTab === "refunds" && (
              <div>
                <div className="p-4 border-b border-slate-200 flex items-center gap-3">
                  <div className="relative flex-1">
                    <input
                      id="refund-search"
                      type="text"
                      placeholder="Search refund ID or status…"
                      value={refundFilter}
                      onChange={(e) => setRefundFilter(e.target.value)}
                      className="w-full bg-white border border-slate-200 shadow-2xs rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0C5ADB] transition"
                    />
                    <svg className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                    </svg>
                  </div>
                  <span className="text-xs text-slate-500 font-mono font-semibold">{filteredRefund.length} rows</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs min-w-[760px]">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/90 text-slate-600 uppercase tracking-wider text-[11px] sticky top-0 backdrop-blur z-10 font-bold">
                        <th className="px-4 py-3.5 text-left">Refund ID</th>
                        <th className="px-4 py-3.5 text-left">Payment</th>
                        <th className="px-4 py-3.5 text-left">Settlement</th>
                        <th className="px-4 py-3.5 text-right">Gateway Amt</th>
                        <th className="px-4 py-3.5 text-right">Ledger Amt</th>
                        <th className="px-4 py-3.5 text-right">Difference</th>
                        <th className="px-4 py-3.5 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      {filteredRefund.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="px-4 py-12 text-center text-slate-500 font-sans text-xs">
                            No records found. Run engines first.
                          </td>
                        </tr>
                      ) : (
                        filteredRefund.map((row) => (
                          <tr key={row.id} className="hover:bg-slate-50/80 transition-colors">
                            <td className="px-4 py-3 font-mono text-xs text-slate-900 font-bold">{row.refund_id}</td>
                            <td className="px-4 py-3 font-mono text-xs text-slate-500">{row.payment_id ?? "—"}</td>
                            <td className="px-4 py-3 font-mono text-xs text-slate-500">{row.settlement_id ?? "—"}</td>
                            <td className="px-4 py-3 text-right text-emerald-700 font-bold tabular-nums">{inr(row.refund_amount_inr)}</td>
                            <td className="px-4 py-3 text-right text-slate-800 tabular-nums">{row.ledger_amount_inr !== null ? inr(row.ledger_amount_inr) : "—"}</td>
                            <td className={`px-4 py-3 text-right font-bold tabular-nums ${row.difference_inr && Math.abs(row.difference_inr) > 0.01 ? "text-rose-600" : "text-slate-400"}`}>
                              {row.difference_inr !== null && row.difference_inr !== 0 ? inr(row.difference_inr) : "—"}
                            </td>
                            <td className="px-4 py-3 text-center font-sans">
                              <StatusPill status={row.refund_status} />
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
