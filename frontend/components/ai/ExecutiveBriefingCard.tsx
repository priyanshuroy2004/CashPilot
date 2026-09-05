"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

interface DailyExceptionSummary {
  as_of: string;
  total_unresolved_cases: number;
  total_value_at_risk_inr: string;
  critical_cases_count: number;
  high_cases_count: number;
  medium_cases_count: number;
  low_cases_count: number;
  summary_text: string;
  highest_priority_case_id?: string | null;
  highest_priority_case_summary?: string | null;
  top_recommended_actions?: string[];
  is_fallback?: boolean;
}

export default function ExecutiveBriefingCard() {
  const [summary, setSummary] = useState<DailyExceptionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/ai/executive-summary");
      if (!res.ok) throw new Error("Failed to load executive briefing");
      const data = await res.json();
      setSummary(data);
    } catch (err: any) {
      setError(err.message || "Failed to load executive briefing");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm animate-pulse space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-5 bg-slate-200 rounded-lg w-1/3" />
          <div className="h-8 bg-slate-200 rounded-lg w-24" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-100 rounded-xl" />
          ))}
        </div>
        <div className="h-20 bg-slate-100 rounded-xl" />
      </div>
    );
  }

  if (error || !summary) {
    return null;
  }

  return (
    <div className="relative rounded-2xl bg-[#0C2340] border border-slate-800 text-white shadow-xl p-6 md:p-7 overflow-hidden">
      {/* Razorpay Brand Gradient Accent Top Line */}
      <div className="absolute top-0 inset-x-0 h-[3px] bg-gradient-to-r from-[#0C5ADB] via-[#00B574] to-[#0C5ADB]" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-white/[0.1]">
        <div className="flex items-start sm:items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-white/[0.08] border border-white/[0.12] flex items-center justify-center shrink-0 text-[#00B574]">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
            </svg>
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-bold text-white tracking-tight">
                Daily Financial Control Briefing
              </h2>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#00B574]/20 text-emerald-300 border border-[#00B574]/30">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00B574] animate-pulse" />
                AI Synthesis
              </span>
              {summary.is_fallback && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Rule-Based Posture
                </span>
              )}
            </div>
            <p className="text-xs text-slate-300 mt-0.5">
              Deterministic cash posture and audit exceptions as of <span className="text-white font-medium">{summary.as_of}</span>
            </p>
          </div>
        </div>

        <button
          onClick={fetchSummary}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-200 hover:text-white bg-white/[0.08] hover:bg-white/[0.14] border border-white/[0.12] transition shadow-xs self-start sm:self-auto cursor-pointer"
        >
          <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          <span>Refresh Briefing</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-5">
        <div className="p-3.5 rounded-xl bg-[#08162B] border border-rose-500/30 col-span-2 sm:col-span-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold block mb-1">
            Total Value at Risk
          </span>
          <span className="text-lg font-extrabold text-rose-400 font-mono tracking-tight">
            {summary.total_value_at_risk_inr}
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-[#08162B] border border-white/[0.08]">
          <span className="text-[10px] text-rose-400 uppercase tracking-wider font-bold block mb-1 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
            Critical
          </span>
          <span className="text-lg font-bold text-white font-mono">
            {summary.critical_cases_count}
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-[#08162B] border border-white/[0.08]">
          <span className="text-[10px] text-amber-400 uppercase tracking-wider font-bold block mb-1">
            High Risk
          </span>
          <span className="text-lg font-bold text-white font-mono">
            {summary.high_cases_count}
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-[#08162B] border border-white/[0.08]">
          <span className="text-[10px] text-blue-400 uppercase tracking-wider font-bold block mb-1">
            Medium
          </span>
          <span className="text-lg font-bold text-white font-mono">
            {summary.medium_cases_count}
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-[#08162B] border border-white/[0.08]">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold block mb-1">
            Low Risk
          </span>
          <span className="text-lg font-bold text-white font-mono">
            {summary.low_cases_count}
          </span>
        </div>
      </div>

      {/* Summary Narrative */}
      <div className="mt-4 p-4 rounded-xl bg-[#08162B] border border-white/[0.08] text-xs sm:text-sm text-slate-200 leading-relaxed relative border-l-4 border-l-[#0C5ADB]">
        <p className="pl-1">{summary.summary_text}</p>
      </div>

      {/* Highest Priority Alert */}
      {summary.highest_priority_case_id && (
        <div className="mt-4 p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              <span className="text-xs font-bold text-rose-300 uppercase tracking-wider">
                Highest Priority Investigation Case
              </span>
              <span className="font-mono text-xs font-bold text-white bg-rose-500/30 border border-rose-500/40 px-2 py-0.5 rounded-md">
                {summary.highest_priority_case_id}
              </span>
            </div>
            <p className="text-xs text-rose-200 leading-relaxed">
              {summary.highest_priority_case_summary}
            </p>
          </div>

          <Link
            href="/exceptions"
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow-md transition whitespace-nowrap self-start sm:self-auto shrink-0"
          >
            Investigate Case →
          </Link>
        </div>
      )}

      {/* Leadership Action Checklist */}
      {summary.top_recommended_actions && summary.top_recommended_actions.length > 0 && (
        <div className="mt-5 space-y-2.5">
          <span className="text-[11px] font-bold text-blue-300 uppercase tracking-wider block">
            Recommended Leadership Directives
          </span>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {summary.top_recommended_actions.map((act, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-[#08162B] border border-white/[0.08] text-xs text-slate-200 flex items-start gap-2.5 hover:border-blue-500/40 transition-colors"
              >
                <span className="w-5 h-5 rounded-full bg-[#0C5ADB]/20 border border-[#0C5ADB]/40 text-blue-300 font-bold flex items-center justify-center shrink-0 text-[10px]">
                  {idx + 1}
                </span>
                <span className="leading-snug">{act}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
