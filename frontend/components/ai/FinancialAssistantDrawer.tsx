"use client";

import React, { useState } from "react";

interface EvidenceRecord {
  record_type: string;
  record_id: string;
  status?: string | null;
  amount_inr?: string | null;
  verified: boolean;
  discrepancy?: string | null;
}

interface FinancialBreakdown {
  gross_amount_inr?: string | null;
  fee_amount_inr?: string | null;
  tax_amount_inr?: string | null;
  refund_adjustment_inr?: string | null;
  other_adjustment_inr?: string | null;
  expected_net_inr?: string | null;
  reported_or_bank_inr?: string | null;
  variance_inr?: string | null;
  status?: string | null;
}

interface AssistantResponse {
  query: string;
  detected_intent: string;
  answer: string;
  explanation: string;
  breakdown?: FinancialBreakdown | null;
  verified_facts?: Record<string, any>;
  evidence_records?: EvidenceRecord[];
  recommended_actions?: string[];
  is_fallback?: boolean;
  disclaimer?: string;
}

const QUICK_PROMPTS = [
  { label: "💰 Cash Position", prompt: "What is our current cash posture and expected liquidity?" },
  { label: "🏦 Missing Settlements", prompt: "Which settlements are missing from the bank?" },
  { label: "📦 Unfulfilled Paid Orders", prompt: "Show me orders paid but not shipped past 72 hours" },
  { label: "📑 Missing Ledger Refunds", prompt: "Are any refunds missing in the accounting ledger?" },
  { label: "🔍 Explain SETL-9001", prompt: "Why did settlement SETL-9001 differ from expected net?" },
  { label: "⚠️ Highest Risk Cases", prompt: "What are our highest risk open exceptions?" },
];

export default function FinancialAssistantDrawer({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<AssistantResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAsk = async (userQuestion?: string) => {
    const q = (userQuestion || query).trim();
    if (!q) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("http://localhost:8000/api/ai/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Assistant query failed");
      }

      const data: AssistantResponse = await res.json();
      setHistory((prev) => [data, ...prev]);
      setQuery("");
    } catch (err: any) {
      setError(err.message || "Failed to reach AI assistant service.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/60 backdrop-blur-sm flex justify-end transition-opacity animate-fadeIn">
      <div className="w-full max-w-full sm:max-w-xl md:max-w-2xl bg-white text-slate-900 border-l border-slate-200 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header - Razorpay Ray Style */}
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-[#00B574] font-bold shrink-0 shadow-sm">
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900 tracking-tight">Ask AI • CASHpilot AI</h2>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00B574] animate-pulse" />
                  Deterministic Grounding
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">Finance Controller Assistant</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close assistant drawer"
            className="p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition cursor-pointer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Quick Suggested Queries */}
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">
            Suggested Queries
          </div>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_PROMPTS.map((qp, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuery(qp.prompt);
                  handleAsk(qp.prompt);
                }}
                disabled={loading}
                className="px-2.5 py-1 rounded-lg bg-white hover:bg-blue-50 border border-slate-200 hover:border-[#0C5ADB] text-xs font-medium text-slate-700 hover:text-[#0C5ADB] transition disabled:opacity-50 cursor-pointer shadow-xs"
              >
                {qp.label}
              </button>
            ))}
          </div>
        </div>

        {/* Conversation Thread */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#F8FAFC]">
          {history.length === 0 && !loading && (
            <div className="h-full min-h-[300px] flex flex-col items-center justify-center text-center p-6 text-slate-500">
              <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center mb-3 text-[#00B574] shadow-sm">
                <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
                </svg>
              </div>
              <p className="text-sm font-bold text-slate-800">Ask any financial or reconciliation inquiry</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm leading-relaxed">
                Ask AI cross-references orders, gateway payouts, tax ledgers, and bank statements with deterministic mathematical certainty.
              </p>
            </div>
          )}

          {loading && (
            <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 flex items-center gap-3 text-sm text-[#0C5ADB] animate-pulse">
              <div className="w-4 h-4 rounded-full border-2 border-[#0C5ADB] border-t-transparent animate-spin shrink-0" />
              <span>Querying verified database records and compiling evidence citations...</span>
            </div>
          )}

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <svg className="w-4 h-4 shrink-0 text-rose-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {history.map((resp, i) => (
            <div key={i} className="space-y-3 p-4 sm:p-5 rounded-2xl bg-white border border-slate-200 shadow-sm">
              {/* Question & Intent */}
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100 gap-2">
                <span className="text-xs font-bold text-slate-900 truncate">“{resp.query}”</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-50 text-[#0C5ADB] border border-blue-200 font-semibold shrink-0">
                  {resp.detected_intent}
                </span>
              </div>

              {/* Direct Answer */}
              <div className="text-sm font-medium text-slate-800 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-200/80">
                {resp.answer}
              </div>

              {/* Context Explanation */}
              {resp.explanation && (
                <div className="text-xs text-slate-600 leading-relaxed pl-1">
                  {resp.explanation}
                </div>
              )}

              {/* Pre-calculated Breakdown Table if present */}
              {resp.breakdown && (
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                    Deterministic Calculation Breakdown
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                      <div className="text-[10px] text-slate-500 font-medium">Gross Sales</div>
                      <div className="font-mono font-bold text-slate-900">{resp.breakdown.gross_amount_inr || "₹0.00"}</div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                      <div className="text-[10px] text-slate-500 font-medium">Gateway Fee</div>
                      <div className="font-mono font-bold text-amber-700">-{resp.breakdown.fee_amount_inr || "₹0.00"}</div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                      <div className="text-[10px] text-slate-500 font-medium">GST (18%)</div>
                      <div className="font-mono font-bold text-amber-700">-{resp.breakdown.tax_amount_inr || "₹0.00"}</div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                      <div className="text-[10px] text-slate-500 font-medium">Net Expected</div>
                      <div className="font-mono font-bold text-emerald-700">{resp.breakdown.expected_net_inr || "₹0.00"}</div>
                    </div>
                  </div>
                  {resp.breakdown.variance_inr && resp.breakdown.variance_inr !== "₹0.00" && (
                    <div className="text-xs flex items-center justify-between p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800">
                      <span>Reported Net Variance:</span>
                      <span className="font-mono font-bold">{resp.breakdown.variance_inr}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Evidence Records */}
              {resp.evidence_records && resp.evidence_records.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    Traceable Evidence Citations ({resp.evidence_records.length})
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {resp.evidence_records.map((rec, rIdx) => (
                      <span
                        key={rIdx}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono border ${
                          rec.verified
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : "bg-rose-50 text-rose-800 border-rose-200"
                        }`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-current" />
                        <span className="text-[10px] text-slate-600">{rec.record_type}:</span>
                        <span className="font-bold">{rec.record_id}</span>
                        {rec.amount_inr && <span className="text-slate-700">({rec.amount_inr})</span>}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommended Next Actions */}
              {resp.recommended_actions && resp.recommended_actions.length > 0 && (
                <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200/80 space-y-1.5">
                  <div className="text-[10px] font-bold text-[#0C5ADB] uppercase tracking-wider">
                    Recommended Actions (Advisory)
                  </div>
                  <ul className="space-y-1.5">
                    {resp.recommended_actions.map((act, aIdx) => (
                      <li key={aIdx} className="text-xs text-slate-700 flex items-start gap-2">
                        <span className="text-[#0C5ADB] font-bold shrink-0">›</span>
                        <span>{act}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Disclaimer */}
              <div className="text-[10px] text-slate-400 italic pt-1 border-t border-slate-100">
                {resp.disclaimer || "AI explains financial data based on verified database records. All financial actions require human approval."}
              </div>
            </div>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-200 bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about settlements, bank deposits, unfulfilled orders..."
              className="flex-1 bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0C5ADB] focus:ring-1 focus:ring-[#0C5ADB] transition"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-4 py-2.5 rounded-xl bg-[#0C5ADB] hover:bg-[#0944A8] disabled:opacity-40 text-white text-xs sm:text-sm font-bold shadow-md shadow-blue-900/20 transition flex items-center gap-1.5 cursor-pointer shrink-0"
            >
              <span>Ask</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
