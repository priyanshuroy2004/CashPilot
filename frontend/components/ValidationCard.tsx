"use client";

import { useState } from "react";
import ColumnMappingPreview from "./ColumnMappingPreview";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");


// ── Type shapes from backend ─────────────────────────────────────────────────
interface ColumnMappingItem {
  original: string;
  normalized: string;
  confidence: "HIGH" | "MEDIUM" | "UNMAPPED";
}
interface ValidationError {
  row: number;
  field: string;
  message: string;
}
export interface FileUploadResult {
  session_id: string;
  filename: string;
  dataset_type: string;
  detection_confidence: string;
  row_count: number;
  valid_count: number;
  error_count: number;
  column_mapping: ColumnMappingItem[];
  errors: ValidationError[];
}

// ── Helpers ──────────────────────────────────────────────────────────────────
const TYPE_COLORS: Record<string, string> = {
  orders:            "bg-blue-50 text-[#0C5ADB] border-blue-200",
  payments:          "bg-indigo-50 text-indigo-700 border-indigo-200",
  settlements:       "bg-emerald-50 text-emerald-800 border-emerald-200",
  settlement_lines:  "bg-teal-50 text-teal-800 border-teal-200",
  bank_transactions: "bg-amber-50 text-amber-800 border-amber-200",
  unknown:           "bg-slate-100 text-slate-700 border-slate-200",
};

const DETECT_CONF_STYLES: Record<string, string> = {
  HIGH:    "text-emerald-700 font-semibold",
  MEDIUM:  "text-amber-700 font-semibold",
  LOW:     "text-orange-700 font-semibold",
  UNKNOWN: "text-rose-700 font-semibold",
};

const TYPE_LABELS: Record<string, string> = {
  orders:            "Orders",
  payments:          "Payments",
  settlements:       "Settlements",
  settlement_lines:  "Settlement Lines",
  bank_transactions: "Bank Transactions",
  unknown:           "Unknown",
};

// ── Component ────────────────────────────────────────────────────────────────
interface Props {
  result: FileUploadResult;
  onCommitSuccess?: (imported: number, skipped: number, dtype: string) => void;
}

type CommitState = "idle" | "loading" | "success" | "error";

export default function ValidationCard({ result, onCommitSuccess }: Props) {
  const [errorsOpen, setErrorsOpen] = useState(false);
  const [commitState, setCommitState] = useState<CommitState>("idle");
  const [commitMsg, setCommitMsg]     = useState("");
  const [importedCount, setImportedCount]   = useState(0);
  const [skippedCount, setSkippedCount]   = useState(0);

  const canImport =
    result.session_id !== "" &&
    result.valid_count > 0 &&
    result.dataset_type !== "unknown";

  const isLoading = commitState === "loading";
  const buttonDisabled = !canImport || isLoading || commitState !== "idle";

  async function handleCommit() {
    setCommitState("loading");
    try {
      const res = await fetch(
        `${API}/api/data/imports/${result.session_id}/commit`,
        { method: "POST" }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Commit failed");
      }
      const data = await res.json();
      setImportedCount(data.imported);
      setSkippedCount(data.skipped);
      setCommitMsg(data.message);
      setCommitState("success");
      onCommitSuccess?.(data.imported, data.skipped, result.dataset_type);
    } catch (err: unknown) {
      setCommitState("error");
      setCommitMsg(err instanceof Error ? err.message : "Unknown error");
    }
  }

  const isKnown = result.dataset_type !== "unknown";

  return (
    <div className={`
      rounded-2xl border overflow-hidden transition-all duration-300
      ${result.error_count === 0 && isKnown
        ? "border-slate-200"
        : result.valid_count > 0
          ? "border-amber-300"
          : "border-rose-300"
      }
      bg-white shadow-xs
    `}>
      {/* ── Header ── */}
      <div className="px-5 py-4 flex items-start gap-4 border-b border-slate-200 bg-slate-50/70">
        {/* File icon */}
        <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-2xs">
          <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        </div>

        <div className="flex-1 min-w-0">
          {/* Filename + type badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-slate-900 truncate max-w-xs">
              {result.filename}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${TYPE_COLORS[result.dataset_type] ?? TYPE_COLORS.unknown}`}>
              {TYPE_LABELS[result.dataset_type] ?? result.dataset_type}
            </span>
            <span className={`text-[10px] font-medium ${DETECT_CONF_STYLES[result.detection_confidence] ?? "text-slate-500"}`}>
              {result.detection_confidence} confidence
            </span>
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-4 mt-2 text-xs">
            <span className="text-slate-500">
              <span className="text-slate-900 font-mono font-bold">{result.row_count.toLocaleString()}</span> rows
            </span>
            {result.valid_count > 0 && (
              <span className="text-emerald-700">
                <span className="font-mono font-bold">{result.valid_count.toLocaleString()}</span> valid
              </span>
            )}
            {result.error_count > 0 && (
              <span className="text-rose-700">
                <span className="font-mono font-bold">{result.error_count.toLocaleString()}</span> invalid
              </span>
            )}
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex-shrink-0 mt-0.5">
          {!isKnown ? (
            <span className="text-[10px] font-bold px-2 py-1 rounded-lg bg-rose-50 text-rose-800 border border-rose-200">
              UNDETECTED
            </span>
          ) : result.error_count === 0 ? (
            <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              ALL VALID
            </span>
          ) : result.valid_count > 0 ? (
            <span className="text-[10px] font-bold px-2 py-1 rounded-lg bg-amber-50 text-amber-900 border border-amber-200">
              PARTIAL
            </span>
          ) : (
            <span className="text-[10px] font-bold px-2 py-1 rounded-lg bg-rose-50 text-rose-800 border border-rose-200">
              ALL FAILED
            </span>
          )}
        </div>
      </div>

      {/* ── Body ── */}
      <div className="px-5 py-4 space-y-4">
        {/* Validation errors */}
        {result.errors.length > 0 && (
          <div>
            <button
              type="button"
              onClick={() => setErrorsOpen((p) => !p)}
              className="flex items-center gap-2 text-sm text-rose-600 hover:text-rose-700 transition-colors duration-150 cursor-pointer"
            >
              <svg
                className={`w-3.5 h-3.5 transition-transform duration-200 ${errorsOpen ? "rotate-90" : ""}`}
                fill="none"
                stroke="currentColor"
                strokeWidth={2.5}
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
              <span className="font-bold text-xs">
                {result.errors.length} validation {result.errors.length === 1 ? "error" : "errors"}
              </span>
            </button>

            {errorsOpen && (
              <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/50 overflow-hidden max-h-56 overflow-y-auto">
                {result.errors.map((err, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 px-4 py-2.5 text-xs border-b border-rose-100 last:border-0"
                  >
                    <span className="font-mono font-bold text-rose-700 w-16 flex-shrink-0">
                      {err.row === 0 ? "FILE" : `Row ${err.row}`}
                    </span>
                    <span className="font-mono text-slate-800 w-28 flex-shrink-0 truncate font-semibold">
                      {err.field}
                    </span>
                    <span className="text-slate-700">{err.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Column mapping preview */}
        {result.column_mapping.length > 0 && isKnown && (
          <ColumnMappingPreview
            mapping={result.column_mapping}
            datasetType={result.dataset_type}
          />
        )}

        {/* Import area */}
        {isKnown && commitState !== "success" && (
          <div className="pt-1">
            <button
              id={`commit-btn-${result.session_id}`}
              type="button"
              onClick={handleCommit}
              disabled={buttonDisabled}
              className={`
                w-full py-3 px-5 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200
                flex items-center justify-center gap-2 cursor-pointer
                ${buttonDisabled
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                  : "bg-[#0C5ADB] hover:bg-[#0944A8] text-white shadow-xs active:scale-[0.98]"
                }
              `}
            >
              {commitState === "loading" ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  Importing…
                </>
              ) : result.valid_count === 0 ? (
                "No valid rows to import"
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  Import {result.valid_count.toLocaleString()} Valid Record{result.valid_count !== 1 ? "s" : ""}
                  {result.error_count > 0 && (
                    <span className="text-xs opacity-75">
                      ({result.error_count} rejected)
                    </span>
                  )}
                </>
              )}
            </button>

            {commitState === "error" && (
              <p className="mt-2 text-xs text-rose-600 text-center font-medium">{commitMsg}</p>
            )}
          </div>
        )}

        {/* Import success */}
        {commitState === "success" && (
          <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-bold text-emerald-800">Import complete</span>
            </div>
            <div className="flex gap-6 text-xs">
              <span className="text-slate-700">
                <span className="text-emerald-700 font-mono font-bold">{importedCount.toLocaleString()}</span> imported
              </span>
              {skippedCount > 0 && (
                <span className="text-slate-500">
                  <span className="font-mono font-semibold">{skippedCount}</span> duplicates skipped
                </span>
              )}
            </div>
            {commitMsg && (
              <p className="text-xs text-slate-500 mt-1">{commitMsg}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
