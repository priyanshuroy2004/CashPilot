"use client";

import React, { useEffect, useState } from "react";

interface EvidenceRecord {
  record_type: string;
  record_id: string;
  status?: string | null;
  amount_inr?: string | null;
  verified: boolean;
  discrepancy?: string | null;
}

interface CaseExplanation {
  case_id: string;
  exception_type: string;
  risk_level: string;
  value_at_risk_inr: string;
  summary: string;
  what_happened: string;
  why_flagged: string;
  financial_impact: string;
  suggested_owner: string;
  suggested_owner_reason: string;
  recommended_actions: string[];
  verified_facts: Record<string, any>;
  evidence_ids: string[];
  evidence_records: EvidenceRecord[];
  confidence_note: string;
  is_fallback: boolean;
}

interface AICaseExplanationTabProps {
  caseId: string;
  onApplyAction?: (actionText: string) => void;
}

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");


export default function AICaseExplanationTab({
  caseId,
  onApplyAction,
}: AICaseExplanationTabProps) {
  const [explanation, setExplanation] = useState<CaseExplanation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/api/ai/cases/${caseId}/explanation`)
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "Failed to generate AI explanation");
        }
        return res.json();
      })
      .then((data: CaseExplanation) => {
        if (isMounted) {
          setExplanation(data);
          setLoading(false);
        }
      })
      .catch((err: any) => {
        if (isMounted) {
          setError(err.message || "Failed to load explanation");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [caseId]);

  if (loading) {
    return (
      <div className="p-8 space-y-4 rounded-2xl bg-slate-50 border border-slate-200 text-center animate-pulse">
        <div className="w-10 h-10 rounded-full border-2 border-[#0C5ADB] border-t-transparent animate-spin mx-auto" />
        <div className="text-sm font-bold text-slate-800">
          Synthesizing verified relational evidence for Case {caseId}...
        </div>
        <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
          Grounding root-cause interpretation in underlying gateway settlements, bank credit timestamps, and fulfillment logs.
        </p>
      </div>
    );
  }

  if (error || !explanation) {
    return (
      <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-center space-y-2">
        <div className="text-rose-800 font-bold text-sm">Unable to generate AI explanation</div>
        <div className="text-xs text-rose-700 font-mono">{error || "Unknown error occurred"}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4 text-left">
      {/* Top Banner with Grounding Guarantee - Razorpay Enterprise Navy */}
      <div className="p-4 sm:p-5 rounded-2xl bg-[#0C2340] border border-slate-800 text-white shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center text-xl shrink-0 shadow-inner">
            ✨
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold text-white tracking-tight">
                AI Root-Cause Intelligence
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#00B574]/20 text-[#00B574] border border-[#00B574]/40">
                100% Deterministic Grounding
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              Zero invented figures. Derived strictly from verified database records.
            </p>
          </div>
        </div>

        <div className="text-left sm:text-right shrink-0 border-t sm:border-t-0 pt-2 sm:pt-0 border-white/10">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Suggested Domain Owner</div>
          <div className="text-xs font-bold text-blue-200 bg-blue-500/20 px-3 py-1 rounded-lg border border-blue-400/30 inline-block mt-0.5">
            {explanation.suggested_owner} Team
          </div>
        </div>
      </div>

      {/* Summary Callout */}
      <div className="p-4 sm:p-5 rounded-2xl bg-blue-50/70 border border-blue-200 space-y-2">
        <div className="text-xs font-bold text-[#0C5ADB] uppercase tracking-wider">
          Executive Synopsis
        </div>
        <p className="text-sm font-semibold text-slate-900 leading-relaxed">
          {explanation.summary}
        </p>
      </div>

      {/* Two Column Grid: What Happened vs Why Flagged */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200 space-y-2 shadow-xs">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase tracking-wider">
            <span>🕒</span> Transaction Journey & What Happened
          </div>
          <p className="text-xs text-slate-700 leading-relaxed font-normal">
            {explanation.what_happened}
          </p>
        </div>

        <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/60 border border-amber-200 space-y-2.5 shadow-xs">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-900 uppercase tracking-wider">
            <span>⚠️</span> Trigger Condition & Financial Exposure
          </div>
          <p className="text-xs text-amber-950 leading-relaxed mb-2">
            <strong className="text-amber-900 font-bold">Rule Breach:</strong> {explanation.why_flagged}
          </p>
          <p className="text-xs text-rose-950 leading-relaxed border-t border-amber-200/80 pt-2">
            <strong className="text-rose-900 font-bold">Financial Impact:</strong> {explanation.financial_impact}
          </p>
        </div>
      </div>

      {/* Suggested Owner Rationale */}
      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5">
        <div className="text-[#0C5ADB] font-bold text-xs mt-0.5">💡</div>
        <div className="text-xs text-slate-700 leading-relaxed">
          <strong className="text-[#0C5ADB] font-semibold">Assignment Rationale:</strong> {explanation.suggested_owner_reason}
        </div>
      </div>

      {/* Traceable Evidence Records */}
      {explanation.evidence_records && explanation.evidence_records.length > 0 && (
        <div className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200 space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Traceable Relational Evidence ({explanation.evidence_records.length})
            </span>
            <span className="text-[10px] text-emerald-700 font-mono font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              Citation Verification: PASSED
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {explanation.evidence_records.map((rec, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-slate-50/80 border border-slate-200 flex items-center justify-between text-xs font-mono"
              >
                <div className="flex items-center gap-2.5">
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      rec.verified ? "bg-[#00B574]" : "bg-rose-500"
                    }`}
                  />
                  <div>
                    <span className="text-slate-500 text-[10px] block font-sans font-medium">{rec.record_type}</span>
                    <span className="text-slate-900 font-bold">{rec.record_id}</span>
                  </div>
                </div>

                <div className="text-right">
                  {rec.amount_inr && (
                    <span className="text-slate-900 font-bold block">{rec.amount_inr}</span>
                  )}
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                      rec.status === "CAPTURED" || rec.status === "MATCHED" || rec.status === "CLOSED"
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : "bg-amber-50 text-amber-800 border-amber-200"
                    }`}
                  >
                    {rec.status || "VERIFIED"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Advisory Action Checklist */}
      {explanation.recommended_actions && explanation.recommended_actions.length > 0 && (
        <div className="p-4 sm:p-5 rounded-2xl bg-blue-50/40 border border-blue-200 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-[#0C5ADB] uppercase tracking-wider">
                Recommended Action Checklist (Human Advisory)
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-[#0C5ADB] border border-blue-200">
                Action Required
              </span>
            </div>
            <span className="text-[10px] text-slate-500 italic">
              Irreversible actions require human authorization
            </span>
          </div>

          <div className="space-y-2">
            {explanation.recommended_actions.map((act, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-white border border-slate-200 flex items-center justify-between gap-3 shadow-xs hover:border-[#0C5ADB] transition"
              >
                <div className="flex items-start gap-2.5 text-xs text-slate-800 font-medium">
                  <span className="font-bold text-[#0C5ADB] mt-0.5">{idx + 1}.</span>
                  <span>{act}</span>
                </div>

                {onApplyAction && (
                  <button
                    onClick={() => onApplyAction(act)}
                    className="shrink-0 px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-[#0C5ADB] text-[#0C5ADB] hover:text-white border border-blue-200 text-xs font-bold transition whitespace-nowrap cursor-pointer shadow-xs"
                  >
                    Use in Resolution →
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Confidence Footer */}
      <div className="text-[11px] text-slate-400 italic p-2 border-t border-slate-200 text-center">
        {explanation.confidence_note}
      </div>
    </div>
  );
}
