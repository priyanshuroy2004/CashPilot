"use client";

import { useState, useEffect, useCallback } from "react";
import {
  runForecastEngine,
  getForecastSummary,
  getForecastUpcoming,
  getAlertsSummary,
  getCashGapAlerts,
  acknowledgeAlert,
} from "@/lib/api";
import type {
  ForecastSummary,
  ForecastRecord,
  AlertsSummary,
  CashGapAlert,
  ForecastRunResponse,
} from "@/types";

function inr(paise: number | undefined | null): string {
  if (paise == null) return "₹0.00";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(paise / 100);
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function SeverityBadge({ severity }: { severity: string }) {
  const s = severity?.toUpperCase();
  const map: Record<string, string> = {
    CRITICAL: "bg-rose-50 text-rose-800 border-rose-200",
    HIGH: "bg-red-50 text-red-800 border-red-200",
    MEDIUM: "bg-amber-50 text-amber-900 border-amber-200",
    LOW: "bg-slate-100 text-slate-700 border-slate-200",
  };
  const dot: Record<string, string> = {
    CRITICAL: "bg-rose-500 animate-ping",
    HIGH: "bg-red-500",
    MEDIUM: "bg-amber-500",
    LOW: "bg-slate-400",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${map[s] ?? map.LOW}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot[s] ?? dot.LOW}`} />
      {s}
    </span>
  );
}

function AlertTypeBadge({ type }: { type: string }) {
  const labels: Record<string, { icon: string; label: string }> = {
    OVERDUE_SETTLEMENT: { icon: "⏰", label: "Overdue Settlement" },
    RISK_GAP: { icon: "🏦", label: "Settlement Risk Gap" },
    SETTLEMENT_DELAY: { icon: "🔄", label: "Settlement Delay" },
  };
  const info = labels[type] ?? { icon: "⚠️", label: type };
  return (
    <span className="flex items-center gap-1.5 text-xs text-slate-800 font-semibold">
      <span>{info.icon}</span>
      <span>{info.label}</span>
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    OPEN: "bg-amber-50 text-amber-900 border-amber-200",
    ACKNOWLEDGED: "bg-blue-50 text-[#0C5ADB] border-blue-200",
    RESOLVED: "bg-emerald-50 text-emerald-800 border-emerald-200",
    PENDING: "bg-blue-50 text-blue-800 border-blue-200",
    OVERDUE: "bg-rose-50 text-rose-800 border-rose-200",
  };
  const cls = map[status?.toUpperCase()] ?? "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${cls}`}>
      {status}
    </span>
  );
}

export default function ForecastPage() {
  const [activeTab, setActiveTab] = useState<"forecast" | "alerts">("forecast");
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<ForecastRunResponse | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // Forecast state
  const [summary, setSummary] = useState<ForecastSummary | null>(null);
  const [forecasts, setForecasts] = useState<ForecastRecord[]>([]);
  const [forecastTotal, setForecastTotal] = useState(0);
  const [forecastPage, setForecastPage] = useState(0);
  const forecastPageSize = 50;

  // Alert state
  const [alertSummary, setAlertSummary] = useState<AlertsSummary | null>(null);
  const [alerts, setAlerts] = useState<CashGapAlert[]>([]);
  const [alertTotal, setAlertTotal] = useState(0);
  const [alertPage, setAlertPage] = useState(0);
  const [alertSevFilter, setAlertSevFilter] = useState("ALL");
  const [acknowledging, setAcknowledging] = useState<string | null>(null);

  const alertPageSize = 50;

  // ── Fetchers ────────────────────────────────────────────────────────────
  const fetchSummary = useCallback(async () => {
    try {
      const s = await getForecastSummary();
      setSummary(s);
    } catch { /* no data yet */ }
  }, []);

  const fetchForecasts = useCallback(async () => {
    try {
      const res = await getForecastUpcoming(undefined, forecastPageSize, forecastPage * forecastPageSize);
      setForecasts(res.items);
      setForecastTotal(res.total);
    } catch { /* no data yet */ }
  }, [forecastPage, forecastPageSize]);

  const fetchAlertSummary = useCallback(async () => {
    try {
      const s = await getAlertsSummary();
      setAlertSummary(s);
    } catch { /* no data yet */ }
  }, []);

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await getCashGapAlerts(
        undefined,
        alertSevFilter !== "ALL" ? alertSevFilter : undefined,
        undefined,
        alertPageSize,
        alertPage * alertPageSize
      );
      setAlerts(res.items);
      setAlertTotal(res.total);
    } catch { /* no data yet */ }
  }, [alertPage, alertPageSize, alertSevFilter]);

  useEffect(() => {
    fetchSummary();
    fetchForecasts();
    fetchAlertSummary();
    fetchAlerts();
  }, [fetchSummary, fetchForecasts, fetchAlertSummary, fetchAlerts]);

  // ── Engine Run ──────────────────────────────────────────────────────────
  const handleRun = async () => {
    setRunning(true);
    setRunResult(null);
    setRunError(null);
    try {
      const res = await runForecastEngine();
      setRunResult(res);
      await Promise.all([fetchSummary(), fetchForecasts(), fetchAlertSummary(), fetchAlerts()]);
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : "Engine run failed.");
    } finally {
      setRunning(false);
    }
  };

  // ── Acknowledge Alert ───────────────────────────────────────────────────
  const handleAcknowledge = async (alertId: string) => {
    setAcknowledging(alertId);
    try {
      await acknowledgeAlert(alertId);
      await Promise.all([fetchAlertSummary(), fetchAlerts()]);
    } catch (err: unknown) {
      alert(`Failed to acknowledge: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setAcknowledging(null);
    }
  };

  // ── Horizon card helper ─────────────────────────────────────────────────
  const horizonData = summary
    ? [
        { days: 1, data: summary.horizon_1_day, color: "bg-[#0C5ADB]" },
        { days: 3, data: summary.horizon_3_days, color: "bg-indigo-600" },
        { days: 7, data: summary.horizon_7_days, color: "bg-violet-600" },
        { days: 14, data: summary.horizon_14_days, color: "bg-[#00B574]" },
      ]
    : [];

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 animate-fadeIn">
      {/* ── Page Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex flex-wrap items-center gap-2.5 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Forecast & Cash-Gap Alerts
            </h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-[#0C5ADB] border border-blue-200">
              <span className="w-2 h-2 rounded-full bg-[#0C5ADB] animate-pulse" />
              Projections Engine
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 leading-relaxed max-w-2xl">
            Forward settlement projections and cash-gap detection for unsettled captured payments.
          </p>
          <p className="text-xs text-amber-900 mt-2 flex items-center gap-1.5 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-xl w-fit font-medium">
            <span>⚠️</span>
            <span>
              All forecast amounts are <strong>EXPECTED</strong> projections only — they do not represent confirmed bank credits.
            </span>
          </p>
        </div>

        <button
          id="run-forecast-btn"
          onClick={handleRun}
          disabled={running}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#0C5ADB] hover:bg-[#0944A8] text-white font-bold text-xs shadow-xs disabled:opacity-50 transition-all cursor-pointer self-start md:self-auto shrink-0"
        >
          {running ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Running Engine…</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
              </svg>
              <span>Run Forecast Engine</span>
            </>
          )}
        </button>
      </div>

      {/* ── Run Result Banner ── */}
      {runResult && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs animate-fadeIn flex items-start justify-between gap-4">
          <div>
            <p className="font-bold text-emerald-800 mb-0.5">✅ {runResult.message}</p>
            <p className="text-emerald-700">
              {runResult.unsettled_payments_count} unsettled payments projected ·{" "}
              {runResult.forecasts_created} forecast records created
              {runResult.gap_detection && (
                <> · {runResult.gap_detection.alerts_created} new cash-gap alerts</>
              )}
            </p>
          </div>
          <button onClick={() => setRunResult(null)} className="text-slate-400 hover:text-slate-700 cursor-pointer">✕</button>
        </div>
      )}
      {runError && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs animate-fadeIn font-medium">
          ⚠️ {runError}
        </div>
      )}

      {/* ── Horizon KPI Cards (EXPECTED amounts) ── */}
      <div className="space-y-3">
        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">
          Expected Cash Inflow — Settlement Projections
        </p>
        {summary ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {horizonData.map(({ days, data, color }) => (
              <div
                key={days}
                className="relative rounded-2xl bg-white p-5 sm:p-6 overflow-hidden border border-slate-200 shadow-xs hover:shadow transition-all duration-200"
              >
                <div className={`absolute inset-x-0 top-0 h-1.5 ${color}`} />
                <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                  Next {days} Day{days > 1 ? "s" : ""}
                </p>
                <p className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
                  {data.expected_amount_inr}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {data.payment_count} payment{data.payment_count !== 1 ? "s" : ""}
                </p>
                <div className="mt-4 px-2.5 py-1 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-[10px] font-bold text-center">
                  EXPECTED · NOT YET RECEIVED
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 3, 7, 14].map((d) => (
              <div key={d} className="rounded-2xl bg-white h-36 animate-pulse border border-slate-200" />
            ))}
          </div>
        )}

        {/* Overdue summary */}
        {summary && summary.total_overdue_count > 0 && (
          <div className="mt-4 p-4 sm:p-5 rounded-2xl bg-rose-50/70 border border-rose-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-center gap-3">
              <span className="text-xl">⏰</span>
              <div>
                <p className="font-bold text-rose-800 text-sm">
                  {summary.total_overdue_count} payment{summary.total_overdue_count !== 1 ? "s" : ""} overdue for settlement
                </p>
                <p className="text-xs text-slate-600 mt-0.5">
                  Total at risk: <span className="text-rose-700 font-mono font-bold">{summary.total_overdue_inr}</span>
                </p>
              </div>
            </div>
            <button
              onClick={() => { setActiveTab("alerts"); }}
              className="px-4 py-2 rounded-xl bg-rose-100 hover:bg-rose-200 text-rose-800 font-bold text-xs border border-rose-300 transition cursor-pointer self-start sm:self-auto"
            >
              View Alerts →
            </button>
          </div>
        )}
      </div>

      {/* ── Tab Switcher ── */}
      <div className="flex items-center gap-1.5 bg-slate-100 p-1.5 rounded-2xl border border-slate-200 w-fit">
        <button
          onClick={() => setActiveTab("forecast")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === "forecast"
              ? "bg-white text-[#0C5ADB] border border-slate-200 shadow-xs"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          📋 Upcoming Settlements ({forecastTotal})
        </button>
        <button
          onClick={() => setActiveTab("alerts")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === "alerts"
              ? "bg-white text-rose-700 border border-slate-200 shadow-xs"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          🚨 Cash-Gap Alerts ({alertSummary?.total_open ?? 0})
        </button>
      </div>

      {/* ── TAB 1: Upcoming Settlements ── */}
      {activeTab === "forecast" && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
          <div className="p-4 sm:p-5 border-b border-slate-200 bg-slate-50/80 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Pending Settlement Forecast</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Captured payments not yet settled — sorted by expected payout date
              </p>
            </div>
            <span className="text-[10px] text-amber-900 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200 font-bold shrink-0">
              EXPECTED ONLY · NOT ACTUAL
            </span>
          </div>

          {forecasts.length === 0 ? (
            <div className="p-16 text-center text-slate-500">
              <div className="text-3xl mb-3">📈</div>
              <p className="text-sm font-bold text-slate-800 mb-1">No forecast records</p>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Click &quot;Run Forecast Engine&quot; to calculate settlement projections.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[760px]">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/90 text-slate-600 font-bold uppercase tracking-wider text-[11px] sticky top-0 backdrop-blur z-10">
                    <th className="py-3.5 px-4">Payment ID</th>
                    <th className="py-3.5 px-4">Order ID</th>
                    <th className="py-3.5 px-4">Gateway</th>
                    <th className="py-3.5 px-4">Expected Amount</th>
                    <th className="py-3.5 px-4">Expected Settlement Date</th>
                    <th className="py-3.5 px-4">Basis</th>
                    <th className="py-3.5 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {forecasts.map((f) => (
                    <tr key={f.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-mono text-slate-900 font-bold">{f.payment_id}</td>
                      <td className="py-3.5 px-4 font-mono text-slate-500">{f.order_id ?? "—"}</td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200 text-[10px] font-bold">
                          {f.gateway ?? "—"}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-amber-800">
                        {f.expected_amount_inr}
                      </td>
                      <td className="py-3.5 px-4 text-slate-700">{fmtDate(f.expected_settlement_date)}</td>
                      <td className="py-3.5 px-4 text-slate-500 text-[10px] font-sans">
                        {f.basis.replace(/_/g, " ")}
                      </td>
                      <td className="py-3.5 px-4 font-sans">
                        <StatusBadge status={f.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Forecast Pagination */}
          {forecastTotal > forecastPageSize && (
            <div className="p-4 border-t border-slate-200 bg-slate-50/80 flex items-center justify-between text-xs text-slate-600">
              <span>
                Showing <span className="font-mono text-slate-900 font-bold">{forecastPage * forecastPageSize + 1}</span>–
                <span className="font-mono text-slate-900 font-bold">{Math.min((forecastPage + 1) * forecastPageSize, forecastTotal)}</span> of{" "}
                <span className="font-mono text-slate-900 font-bold">{forecastTotal}</span> records
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setForecastPage((p) => Math.max(0, p - 1))}
                  disabled={forecastPage === 0}
                  className="px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white text-slate-700 disabled:opacity-40 hover:bg-slate-100 shadow-2xs transition cursor-pointer font-medium"
                >
                  Previous
                </button>
                <button
                  onClick={() => setForecastPage((p) => p + 1)}
                  disabled={(forecastPage + 1) * forecastPageSize >= forecastTotal}
                  className="px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white text-slate-700 disabled:opacity-40 hover:bg-slate-100 shadow-2xs transition cursor-pointer font-medium"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: Cash-Gap Alerts ── */}
      {activeTab === "alerts" && (
        <div className="space-y-4">
          {/* Alert KPI strip */}
          {alertSummary && (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {[
                { label: "Total Open", value: alertSummary.total_open, color: "text-slate-900" },
                { label: "Critical", value: alertSummary.critical_count, color: "text-rose-700" },
                { label: "High", value: alertSummary.high_count, color: "text-red-700" },
                { label: "Medium", value: alertSummary.medium_count, color: "text-amber-800" },
                { label: "Low", value: alertSummary.low_count, color: "text-slate-700" },
              ].map((item) => (
                <div key={item.label} className="p-4 rounded-2xl bg-white border border-slate-200 text-center shadow-xs">
                  <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">{item.label}</p>
                  <p className={`text-2xl font-extrabold font-mono mt-1 ${item.color}`}>{item.value}</p>
                </div>
              ))}
            </div>
          )}

          {alertSummary && alertSummary.total_risk_paise > 0 && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-center">
              <span className="text-rose-800 font-medium">Total Risk Exposure: </span>
              <span className="text-rose-700 font-mono font-bold text-sm">
                {alertSummary.total_risk_inr}
              </span>
            </div>
          )}

          {/* Filter row */}
          <div className="flex items-center gap-3 p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <select
              value={alertSevFilter}
              onChange={(e) => { setAlertSevFilter(e.target.value); setAlertPage(0); }}
              className="bg-white text-slate-800 border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-semibold focus:outline-none focus:border-[#0C5ADB] cursor-pointer shadow-2xs"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
            <span className="text-xs text-slate-500 font-mono font-semibold">{alertTotal} alert{alertTotal !== 1 ? "s" : ""}</span>
          </div>

          {/* Alerts table */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
            {alerts.length === 0 ? (
              <div className="p-16 text-center text-slate-500">
                <div className="text-3xl mb-3">✅</div>
                <p className="text-sm font-bold text-slate-800 mb-1">No Cash-Gap Alerts</p>
                <p className="text-xs text-slate-500 max-w-xs mx-auto">
                  All settlements are on track. Run the forecast engine to detect new gaps.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs min-w-[760px]">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/90 text-slate-600 font-bold uppercase tracking-wider text-[11px] sticky top-0 backdrop-blur z-10">
                      <th className="py-3.5 px-4">Alert ID</th>
                      <th className="py-3.5 px-4">Type</th>
                      <th className="py-3.5 px-4">Severity</th>
                      <th className="py-3.5 px-4">Related Entity</th>
                      <th className="py-3.5 px-4">Gap</th>
                      <th className="py-3.5 px-4">Amount at Risk</th>
                      <th className="py-3.5 px-4">Expected By</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {alerts.map((a) => (
                      <tr key={a.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3.5 px-4 font-mono text-slate-900 font-bold">{a.alert_id}</td>
                        <td className="py-3.5 px-4 font-sans"><AlertTypeBadge type={a.alert_type} /></td>
                        <td className="py-3.5 px-4 font-sans"><SeverityBadge severity={a.severity} /></td>
                        <td className="py-3.5 px-4 font-mono text-slate-600 text-[10px]">
                          {a.payment_id ?? a.settlement_id ?? a.order_id ?? "—"}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`font-bold font-mono ${a.gap_days > 7 ? "text-rose-700" : a.gap_days > 3 ? "text-red-700" : "text-amber-800"}`}>
                            {a.gap_days}d
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-mono font-bold text-slate-900">{a.gap_amount_inr}</td>
                        <td className="py-3.5 px-4 text-slate-700">{fmtDate(a.expected_date)}</td>
                        <td className="py-3.5 px-4 font-sans"><StatusBadge status={a.status} /></td>
                        <td className="py-3.5 px-4 text-right font-sans">
                          {a.status === "OPEN" && (
                            <button
                              onClick={() => handleAcknowledge(a.alert_id)}
                              disabled={acknowledging === a.alert_id}
                              className="px-3 py-1 rounded-lg text-xs font-bold bg-blue-50 hover:bg-blue-100 text-[#0C5ADB] border border-blue-200 transition disabled:opacity-50 cursor-pointer"
                            >
                              {acknowledging === a.alert_id ? "…" : "Acknowledge"}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Alert Pagination */}
            {alertTotal > alertPageSize && (
              <div className="p-4 border-t border-slate-200 bg-slate-50/80 flex items-center justify-between text-xs text-slate-600">
                <span>
                  Showing <span className="font-mono text-slate-900 font-bold">{alertPage * alertPageSize + 1}</span>–
                  <span className="font-mono text-slate-900 font-bold">{Math.min((alertPage + 1) * alertPageSize, alertTotal)}</span> of{" "}
                  <span className="font-mono text-slate-900 font-bold">{alertTotal}</span>
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setAlertPage((p) => Math.max(0, p - 1))}
                    disabled={alertPage === 0}
                    className="px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white text-slate-700 disabled:opacity-40 hover:bg-slate-100 shadow-2xs transition cursor-pointer font-medium"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setAlertPage((p) => p + 1)}
                    disabled={(alertPage + 1) * alertPageSize >= alertTotal}
                    className="px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white text-slate-700 disabled:opacity-40 hover:bg-slate-100 shadow-2xs transition cursor-pointer font-medium"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
