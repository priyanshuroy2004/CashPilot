"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { loadDemoData, clearDemoData, uploadFiles } from "@/lib/api";
import type { DemoLoadResponse, FileUploadResult } from "@/types";
import FileDropzone from "@/components/FileDropzone";
import ValidationCard from "@/components/ValidationCard";


// ── Types ────────────────────────────────────────────────────────────────────
type Tab = "demo" | "upload";
type LoadState = "idle" | "loading" | "success" | "error";
type UploadState = "idle" | "uploading" | "done" | "error";

interface CountRow {
  label: string;
  key: keyof DemoLoadResponse;
  icon: string;
  color: string;
}

const COUNT_ROWS: CountRow[] = [
  { label: "Orders",            key: "orders",            icon: "📦", color: "text-blue-400"   },
  { label: "Payments",          key: "payments",          icon: "💳", color: "text-indigo-400" },
  { label: "Settlements",       key: "settlements",       icon: "🏦", color: "text-emerald-400"},
  { label: "Settlement Lines",  key: "settlement_lines",  icon: "📋", color: "text-teal-400"   },
  { label: "Bank Transactions", key: "bank_transactions", icon: "🏧", color: "text-amber-400"  },
];

// ── Tabs ─────────────────────────────────────────────────────────────────────
function TabButton({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 sm:px-5 py-2.5 text-xs sm:text-sm font-bold rounded-2xl transition-all cursor-pointer ${
        active
          ? "bg-white text-[#0C5ADB] border border-slate-200 shadow-xs"
          : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
      }`}
    >
      {children}
    </button>
  );
}

// ── Demo Data Tab ────────────────────────────────────────────────────────────
function DemoTab() {
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [result, setResult]       = useState<DemoLoadResponse | null>(null);
  const [error, setError]         = useState<string | null>(null);
  const [clearing, setClearing]   = useState(false);
  const [clearMsg, setClearMsg]   = useState<string | null>(null);

  async function handleLoad() {
    setLoadState("loading");
    setError(null);
    setResult(null);
    setClearMsg(null);
    try {
      const data = await loadDemoData();
      setResult(data);
      setLoadState("success");
    } catch (err: unknown) {
      setLoadState("error");
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function handleClear() {
    if (!window.confirm("Are you sure you want to reset the database? This will clear all transactions and reset CASHpilot AI back to its initial onboarding state.")) {
      return;
    }
    setClearing(true);
    setError(null);
    setResult(null);
    setClearMsg(null);
    try {
      const res = await clearDemoData();
      setClearMsg(res.message || "All data cleared successfully. Database is now in initial clean state.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to clear database");
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Card */}
      <div className="rounded-3xl border border-slate-200 bg-white shadow-xs overflow-hidden">
        {/* Card header */}
        <div className="p-5 sm:p-6 border-b border-slate-200/80 flex items-center gap-4 bg-slate-50/80">
          <div className="w-11 h-11 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
            <svg className="w-5 h-5 text-[#0C5ADB]" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">Demo Merchant Dataset</h2>
            <p className="text-xs text-slate-500 mt-0.5">Synthetic e-commerce database: orders, payments, settlements, and bank credits</p>
          </div>
        </div>

        {/* Card body */}
        <div className="p-5 sm:p-6">
          <div className="rounded-2xl bg-blue-50/50 border border-blue-100/80 p-4 mb-6 text-xs sm:text-sm text-slate-700 leading-relaxed">
            Loads a coherent synthetic e-commerce dataset into PostgreSQL. Existing demo data
            will be cleared before loading. The dataset includes{" "}
            <span className="text-slate-900 font-semibold">realistic exception cases</span> such as
            missing payments, amount mismatches, in-transit settlements, and unmatched bank credits.
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3">
            <button
              id="load-demo-btn"
              onClick={handleLoad}
              disabled={loadState === "loading" || clearing}
              className={`
                flex-1 w-full py-3.5 px-6 rounded-2xl font-bold text-xs sm:text-sm transition-all duration-200
                flex items-center justify-center gap-2.5 shadow-xs cursor-pointer
                ${loadState === "loading" || clearing
                  ? "bg-slate-200 text-slate-500 cursor-not-allowed border border-slate-300"
                  : "bg-[#0C5ADB] hover:bg-[#0944A8] text-white shadow-sm hover:shadow active:scale-[0.99]"
                }
              `}
            >
              {loadState === "loading" ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <span>Loading Demo Data…</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  <span>Load Demo Merchant Data</span>
                </>
              )}
            </button>

            <button
              id="clear-demo-btn"
              onClick={handleClear}
              disabled={loadState === "loading" || clearing}
              className={`
                w-full sm:w-auto py-3.5 px-6 rounded-2xl font-bold text-xs sm:text-sm transition-all duration-200
                flex items-center justify-center gap-2 border shadow-xs cursor-pointer
                ${clearing
                  ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed"
                  : "bg-white text-slate-700 hover:text-rose-600 border-slate-200 hover:border-rose-300 hover:bg-rose-50/50 active:scale-[0.99]"
                }
              `}
            >
              {clearing ? (
                <>
                  <svg className="animate-spin w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <span>Resetting…</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                  <span>Clear / Reset Data</span>
                </>
              )}
            </button>
          </div>

          {clearMsg && (
            <div className="mt-4 p-4 rounded-2xl bg-amber-50 border border-amber-200 text-xs sm:text-sm text-amber-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span>🗑️</span>
                <span>{clearMsg}</span>
              </div>
              <Link href="/" className="font-bold text-[#0C5ADB] hover:underline shrink-0">
                View Welcome Onboarding Screen →
              </Link>
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs sm:text-sm text-rose-800">
              {error}
            </div>
          )}
        </div>


        {/* Result panel */}
        {loadState === "success" && result && (
          <div className="px-5 sm:px-6 pb-6">
            <div className="flex items-center gap-2.5 mb-5 px-4 py-3 rounded-2xl bg-emerald-50 border border-emerald-200">
              <svg className="w-5 h-5 text-[#00B574] shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-bold text-emerald-800">Demo data loaded successfully</span>
            </div>
            <div className="rounded-2xl border border-slate-200 overflow-hidden bg-white shadow-xs">
              <table className="w-full text-xs" id="demo-counts-table">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left px-4 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Dataset</th>
                    <th className="text-right px-4 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Records</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {COUNT_ROWS.map((row) => (
                    <tr key={row.key} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-3 flex items-center gap-2.5">
                        <span className="text-base">{row.icon}</span>
                        <span className="text-slate-800 font-semibold">{row.label}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">
                        {(result[row.key] as number).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-slate-50 border-t border-slate-200">
                    <td className="px-4 py-3 text-xs font-bold text-slate-700">Total Records Loaded</td>
                    <td className="px-4 py-3 text-right text-sm font-mono font-extrabold text-[#0C5ADB]">
                      {COUNT_ROWS.reduce((s, r) => s + (result[r.key] as number), 0).toLocaleString()}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <p className="text-xs text-slate-500 mt-3 text-center">
              Click the button again anytime to reload and reset all demo data.
            </p>
          </div>
        )}

        {loadState === "error" && error && (
          <div className="px-5 sm:px-6 pb-6">
            <div className="flex items-start gap-3 p-4 rounded-2xl bg-rose-50 border border-rose-200">
              <svg className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm font-bold text-rose-800">Load failed</p>
                <p className="text-xs text-rose-700 mt-1 font-mono">{error}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Dataset coverage info */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-3xl border border-slate-200 bg-white shadow-xs p-5">
          <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">Dataset Coverage</p>
          <ul className="space-y-2">
            {[
              "290 normal paid orders",
              "10 missing payment cases",
              "5 payment amount mismatches",
              "10 failed payments",
              "4 settlements missing bank credit",
              "3 delayed bank credits",
              "4 orphan bank entries",
            ].map((item) => (
              <li key={item} className="flex items-center gap-2 text-xs text-slate-700">
                <span className="w-2 h-2 rounded-full bg-[#0C5ADB] shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white shadow-xs p-5">
          <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">API Endpoints</p>
          <ul className="space-y-2.5">
            {[
              { method:"GET",  path:"/api/health",      desc:"Health check" },
              { method:"POST", path:"/api/demo/load",   desc:"Load demo"    },
              { method:"POST", path:"/api/data/upload", desc:"Upload CSV"   },
              { method:"GET",  path:"/api/data/imports",desc:"Import history"},
              { method:"GET",  path:"/docs",            desc:"Swagger UI"   },
            ].map((ep) => (
              <li key={ep.path} className="flex items-center justify-between text-xs gap-2">
                <div className="flex items-center gap-2 truncate">
                  <span className={`font-mono font-bold text-[10px] px-2 py-0.5 rounded-md ${ep.method === "GET" ? "bg-emerald-50 text-emerald-700 border border-emerald-200":"bg-blue-50 text-blue-700 border border-blue-200"}`}>{ep.method}</span>
                  <code className="text-slate-700 font-mono text-xs truncate">{ep.path}</code>
                </div>
                <span className="text-slate-400 text-[11px] shrink-0">{ep.desc}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ── Upload Tab ───────────────────────────────────────────────────────────────
function UploadTab() {
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [results, setResults]         = useState<FileUploadResult[]>([]);
  const [error, setError]             = useState<string | null>(null);
  const [importSummary, setImportSummary] = useState<
    { type: string; imported: number; skipped: number }[]
  >([]);

  const handleFiles = useCallback(async (files: File[]) => {
    setUploadState("uploading");
    setError(null);
    setResults([]);
    setImportSummary([]);
    try {
      const response = await uploadFiles(files);
      setResults(response.files);
      setUploadState("done");
    } catch (err: unknown) {
      setUploadState("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }, []);

  function handleCommitSuccess(imported: number, skipped: number, dtype: string) {
    setImportSummary((prev) => [...prev, { type: dtype, imported, skipped }]);
  }

  function handleReset() {
    setUploadState("idle");
    setResults([]);
    setError(null);
    setImportSummary([]);
  }

  const totalImported = importSummary.reduce((s, x) => s + x.imported, 0);

  return (
    <div className="space-y-6">
      {/* Header card */}
      <div className="rounded-3xl border border-slate-200 bg-white shadow-xs overflow-hidden">
        <div className="p-5 sm:p-6 border-b border-slate-200/80 bg-slate-50/80">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight">Upload Finance Data</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Upload your business CSV files — data type is auto-detected from column headers
              </p>
            </div>
            {results.length > 0 && (
              <button
                type="button"
                onClick={handleReset}
                className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors border border-slate-200 px-3.5 py-1.5 rounded-xl hover:bg-slate-100 self-start sm:self-auto cursor-pointer"
              >
                Clear & upload new
              </button>
            )}
          </div>
        </div>

        <div className="p-5 sm:p-6">
          {/* Supported file types */}
          <div className="flex flex-wrap gap-2 mb-5">
            {["orders.csv","payments.csv","settlements.csv","settlement_lines.csv","bank_statement.csv"].map((f) => (
              <span key={f} className="text-[11px] font-mono px-2.5 py-1 rounded-xl bg-slate-100 text-slate-700 border border-slate-200 font-semibold">
                {f}
              </span>
            ))}
          </div>

          {/* Dropzone */}
          <FileDropzone
            onFilesSelected={handleFiles}
            disabled={uploadState === "uploading"}
          />

          {/* Upload loading */}
          {uploadState === "uploading" && (
            <div className="mt-4 flex items-center gap-3 text-xs sm:text-sm text-[#0C5ADB] p-3.5 rounded-2xl bg-blue-50 border border-blue-200 animate-pulse">
              <div className="w-4 h-4 border-2 border-[#0C5ADB] border-t-transparent rounded-full animate-spin shrink-0" />
              <span className="font-semibold">Uploading and validating schema columns…</span>
            </div>
          )}

          {/* Upload error */}
          {uploadState === "error" && error && (
            <div className="mt-4 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs sm:text-sm text-rose-700 flex items-center gap-2">
              <span className="font-bold">Upload failed:</span>
              <span className="font-mono text-xs">{error}</span>
            </div>
          )}
        </div>

        {/* Amount note */}
        <div className="px-5 sm:px-6 pb-5">
          <p className="text-[11px] text-slate-600 bg-amber-50/60 border border-amber-200/80 rounded-2xl p-3 leading-relaxed">
            <span className="text-amber-800 font-bold">Note:</span>{" "}
            Amounts can be formatted in standard rupees (e.g. 1500.00) or integer paise (e.g. 150000) — the validator auto-detects and standardizes values.
          </p>
        </div>
      </div>

      {/* Import summary banner */}
      {importSummary.length > 0 && (
        <div className="rounded-3xl border border-emerald-200 bg-emerald-50/80 p-5 shadow-xs">
          <p className="text-sm font-bold text-emerald-800 mb-3 flex items-center gap-2">
            <svg className="w-5 h-5 text-[#00B574]" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{totalImported.toLocaleString()} records committed to database</span>
          </p>
          <div className="space-y-1.5">
            {importSummary.map((s, i) => (
              <div key={i} className="flex items-center gap-3 text-xs text-slate-700">
                <span className="font-mono text-slate-900 w-32 font-semibold">{s.type}</span>
                <span className="text-[#00B574] font-mono font-bold">{s.imported} imported</span>
                {s.skipped > 0 && <span className="text-slate-400">({s.skipped} skipped duplicates)</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Per-file validation cards */}
      {results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900">
              Validation Dossiers
            </h3>
            <span className="text-xs text-slate-500 font-mono font-medium">
              {results.length} {results.length === 1 ? "file" : "files"}
            </span>
          </div>

          {results.map((r, i) => (
            <ValidationCard
              key={r.session_id || i}
              result={r}
              onCommitSuccess={handleCommitSuccess}
            />
          ))}
        </div>
      )}

      {/* Empty state hint */}
      {uploadState === "idle" && (
        <div className="rounded-3xl border border-dashed border-slate-300 p-8 text-center bg-white/70">
          <p className="text-xs sm:text-sm text-slate-500 font-medium">
            Drag & drop CSV files above to start schema validation. Files are verified before any row is committed to the database.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function DataPage() {
  const [activeTab, setActiveTab] = useState<Tab>("demo");

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6 sm:space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">Data Management</h1>
        <p className="text-slate-500 mt-1 text-xs sm:text-sm leading-relaxed">
          Load demo merchant data for instant exploration or upload and validate custom CSV ledgers.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1.5 bg-slate-100 rounded-2xl p-1.5 border border-slate-200/80 w-fit">
        <TabButton active={activeTab === "demo"} onClick={() => setActiveTab("demo")}>
          🏪 Demo Merchant Dataset
        </TabButton>
        <TabButton active={activeTab === "upload"} onClick={() => setActiveTab("upload")}>
          📂 Custom CSV Uploader
        </TabButton>
      </div>

      {/* Tab content */}
      {activeTab === "demo" ? <DemoTab /> : <UploadTab />}
    </div>
  );
}
