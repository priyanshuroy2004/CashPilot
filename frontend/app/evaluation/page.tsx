"use client";

import { useState, useEffect, useCallback } from "react";
import { getEvaluationMetrics } from "@/lib/api";
import type { EvaluationMetrics } from "@/types";

function pct(v: number | undefined | null): string {
  if (v == null) return "—";
  return `${v.toFixed(1)}%`;
}

function fmtLocalTime(iso: string | undefined | null): string {
  if (!iso) return "—";
  try {
    const s = iso.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z";
    return new Date(s).toLocaleString("en-IN");
  } catch {
    return iso;
  }
}

function MetricCard({
  title,
  icon,
  accent,
  children,
}: {
  title: string;
  icon: string;
  accent: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative rounded-2xl bg-white p-5 sm:p-6 overflow-hidden border border-slate-200 shadow-xs hover:shadow transition-all duration-200">
      <div className={`absolute inset-x-0 top-0 h-1.5 ${accent}`} />
      <div className="flex items-center gap-2.5 mb-4">
        <span className="text-xl">{icon}</span>
        <h3 className="text-sm font-bold text-slate-900 tracking-tight">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function AccuracyBar({ value, label }: { value: number; label?: string }) {
  const color =
    value >= 90 ? "bg-[#00B574]" : value >= 70 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="space-y-1.5">
      {label && <p className="text-xs text-slate-500 font-medium">{label}</p>}
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden border border-slate-200">
          <div
            className={`h-full rounded-full transition-all duration-700 ${color}`}
            style={{ width: `${Math.min(100, value)}%` }}
          />
        </div>
        <span
          className={`text-sm font-extrabold font-mono ${
            value >= 90 ? "text-emerald-700" : value >= 70 ? "text-amber-700" : "text-rose-700"
          }`}
        >
          {pct(value)}
        </span>
      </div>
    </div>
  );
}

function StatRow({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-xs text-slate-500">{label}</span>
      <div className="text-right">
        <span className="text-xs font-bold text-slate-900 font-mono">{value}</span>
        {sub && <p className="text-[10px] text-slate-400">{sub}</p>}
      </div>
    </div>
  );
}

function ByTypeList({ data, title }: { data: Record<string, number>; title: string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return <p className="text-xs text-slate-400">No data</p>;
  return (
    <div className="space-y-2 mt-2">
      {entries.map(([key, val]) => (
        <div key={key} className="flex items-center justify-between text-xs">
          <span className="text-slate-700 truncate max-w-[200px]" title={key}>
            {key.replace(/_/g, " ")}
          </span>
          <span className="font-mono font-bold text-slate-900 px-2 py-0.5 rounded bg-slate-100 border border-slate-200">{val}</span>
        </div>
      ))}
    </div>
  );
}

export default function EvaluationPage() {
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMetrics = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await getEvaluationMetrics();
      setMetrics(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load metrics");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchMetrics(); }, [fetchMetrics]);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex flex-wrap items-center gap-2.5 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Evaluation Dashboard
            </h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-[#0C5ADB] border border-blue-200">
              <span className="w-2 h-2 rounded-full bg-[#0C5ADB] animate-pulse" />
              Performance & Accuracy
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
            Reconciliation quality metrics, ground truth precision, and exception detection performance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {metrics && (
            <p className="text-xs text-slate-500 font-mono">
              Generated: {fmtLocalTime(metrics.generated_at)}
            </p>
          )}
          <button
            onClick={() => fetchMetrics(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#0C5ADB] hover:bg-[#0944A8] text-white text-xs font-bold transition-all shadow-xs disabled:opacity-50 cursor-pointer"
          >
            {refreshing ? (
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <span>↻</span>
            )}
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Ground truth disclaimer */}
      <div className="p-5 rounded-2xl bg-blue-50/70 border border-blue-200 text-xs text-blue-900 flex items-start gap-3.5 shadow-xs">
        <span className="text-xl shrink-0">🔬</span>
        <div>
          <p className="font-bold mb-0.5 text-sm text-slate-900">Evaluation-Only Mode</p>
          <p className="text-slate-700 leading-relaxed">
            {metrics?.ground_truth.note ??
              "Ground truth data is used only for evaluation and never affects production reconciliation, forecasting, or exception detection logic."}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs sm:text-sm flex items-center gap-2">
          <span>⚠️</span>
          <span>{error} — Ensure the backend is running and data has been loaded.</span>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-2xl bg-white h-56 animate-pulse border border-slate-200" />
          ))}
        </div>
      ) : metrics ? (
        <>
          {/* ── Row 1: Core accuracy metrics ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Reconciliation */}
            <MetricCard title="Order-Payment Reconciliation" icon="🔄" accent="bg-[#00B574]">
              <AccuracyBar value={metrics.reconciliation.accuracy_pct} label="Match accuracy" />
              <div className="mt-4 space-y-0">
                <StatRow label="Total records" value={metrics.reconciliation.total_records} />
                <StatRow label="Matched" value={metrics.reconciliation.matched} />
                <StatRow
                  label="Unmatched"
                  value={metrics.reconciliation.total_records - metrics.reconciliation.matched}
                />
              </div>
            </MetricCard>

            {/* Settlement Calculations */}
            <MetricCard title="Settlement Calculations" icon="📑" accent="bg-[#0C5ADB]">
              <AccuracyBar value={metrics.settlement_calculations.accuracy_pct} label="Calculation accuracy" />
              <div className="mt-4 space-y-0">
                <StatRow label="Total settlements" value={metrics.settlement_calculations.total} />
                <StatRow label="Correct" value={metrics.settlement_calculations.correct} />
                <StatRow label="Discrepancy" value={metrics.settlement_calculations.discrepancy} />
                <StatRow label="Discrepancy rate" value={pct(metrics.settlement_calculations.discrepancy_rate_pct)} />
              </div>
            </MetricCard>

            {/* Refund Reconciliation */}
            <MetricCard title="Refund Reconciliation" icon="🔃" accent="bg-teal-500">
              <AccuracyBar value={metrics.refund_reconciliation.accuracy_pct} label="Refund match accuracy" />
              <div className="mt-4 space-y-0">
                <StatRow label="Total refunds" value={metrics.refund_reconciliation.total} />
                <StatRow label="Matched" value={metrics.refund_reconciliation.matched} />
              </div>
              <div className="mt-4 pt-2 border-t border-slate-100">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">By Status</p>
                <ByTypeList data={metrics.refund_reconciliation.by_status} title="Refund status" />
              </div>
            </MetricCard>
          </div>

          {/* ── Row 2: Detection & Resolution ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Tax Reconciliation */}
            <MetricCard title="Tax Line Matching" icon="🧾" accent="bg-amber-500">
              <AccuracyBar value={metrics.tax_reconciliation.accuracy_pct} label="Tax line match rate" />
              <div className="mt-4 space-y-0">
                <StatRow label="Total checks" value={metrics.tax_reconciliation.total} />
                <StatRow label="Matched" value={metrics.tax_reconciliation.matched} />
                <StatRow
                  label="Issues"
                  value={metrics.tax_reconciliation.total - metrics.tax_reconciliation.matched}
                />
              </div>
            </MetricCard>

            {/* Exception Detection */}
            <MetricCard title="Exception Detection" icon="🔍" accent="bg-rose-500">
              <div className="space-y-0 mb-3">
                <StatRow label="Total orders" value={metrics.exception_detection.total_orders} />
                <StatRow label="Exceptions detected" value={metrics.exception_detection.total_exceptions} />
                <StatRow label="Detection rate" value={pct(metrics.exception_detection.detection_rate_pct)} />
              </div>
              <div className="pt-2 border-t border-slate-100">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">By Exception Type</p>
                <ByTypeList data={metrics.exception_detection.by_type} title="Exception types" />
              </div>
            </MetricCard>

            {/* Resolution Performance */}
            <MetricCard title="Resolution Performance" icon="⚡" accent="bg-[#0C5ADB]">
              <div className="space-y-0 mb-3">
                <StatRow
                  label="Avg. resolution time"
                  value={
                    metrics.resolution_performance.avg_resolution_hours != null
                      ? `${metrics.resolution_performance.avg_resolution_hours}h`
                      : "N/A"
                  }
                  sub="Hours from detection to resolution"
                />
                <StatRow label="Total resolved" value={metrics.resolution_performance.resolved_cases} />
                <StatRow label="Total open" value={metrics.resolution_performance.total_open_cases} />
              </div>
              <div className="pt-2 border-t border-slate-100">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Open Cases by Risk</p>
                <ByTypeList data={metrics.resolution_performance.open_by_risk} title="Risk levels" />
              </div>
            </MetricCard>
          </div>

          {/* ── Row 3: Audit & Posture ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Audit Trail */}
            <MetricCard title="Audit Trail Coverage" icon="📋" accent="bg-indigo-600">
              <StatRow label="Total audit events logged" value={metrics.audit_trail.total_events} />
              <div className="mt-4 pt-2 border-t border-slate-100">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Events by Type</p>
                <ByTypeList data={metrics.audit_trail.by_event_type} title="Event types" />
              </div>
            </MetricCard>

            {/* Case Status Distribution */}
            <MetricCard title="Case Status Distribution" icon="📊" accent="bg-slate-700">
              <ByTypeList
                data={metrics.resolution_performance.status_distribution}
                title="Case statuses"
              />
              <div className="mt-4 pt-3 border-t border-slate-100">
                <StatRow
                  label="Total captured payments"
                  value={metrics.payment_posture.total_captured_payments}
                  sub="May be unsettled — see Forecast page"
                />
              </div>
            </MetricCard>
          </div>
        </>
      ) : null}
    </div>
  );
}
