"use client";

import { useState } from "react";

interface MappingItem {
  original: string;
  normalized: string;
  confidence: "HIGH" | "MEDIUM" | "UNMAPPED";
}

interface ColumnMappingPreviewProps {
  mapping: MappingItem[];
  datasetType: string;
}

const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH:    "bg-emerald-50 text-emerald-800 border-emerald-200",
  MEDIUM:  "bg-amber-50  text-amber-800  border-amber-200",
  UNMAPPED:"bg-slate-100   text-slate-600   border-slate-200",
};

export default function ColumnMappingPreview({
  mapping,
  datasetType,
}: ColumnMappingPreviewProps) {
  const [open, setOpen] = useState(false);

  const mappedCount   = mapping.filter((m) => m.confidence !== "UNMAPPED").length;
  const unmappedCount = mapping.filter((m) => m.confidence === "UNMAPPED").length;

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 transition-colors duration-150 cursor-pointer"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform duration-200 ${open ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        <span className="font-semibold text-xs text-slate-800">Column Mapping</span>
        <span className="text-xs font-mono font-bold text-[#0C5ADB]">{mappedCount} mapped</span>
        {unmappedCount > 0 && (
          <span className="text-xs font-mono text-slate-400">({unmappedCount} passthrough)</span>
        )}
      </button>

      {open && (
        <div className="mt-3 rounded-xl border border-slate-200 overflow-hidden bg-white shadow-xs">
          {/* Header */}
          <div className="grid grid-cols-[1fr_auto_1fr_auto] gap-x-3 items-center px-4 py-2 bg-slate-50 border-b border-slate-200">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Original Column</span>
            <span />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Normalized Name</span>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider text-right">Confidence</span>
          </div>

          {/* Rows */}
          <div className="divide-y divide-slate-100 max-h-56 overflow-y-auto">
            {mapping.map((item, i) => (
              <div
                key={i}
                className={`grid grid-cols-[1fr_auto_1fr_auto] gap-x-3 items-center px-4 py-2.5 text-xs hover:bg-slate-50/50 transition-colors ${
                  item.confidence === "UNMAPPED" ? "opacity-60" : ""
                }`}
              >
                <code className="text-slate-800 font-mono truncate">{item.original}</code>
                <svg className="w-3 h-3 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 8.25L21 12m0 0l-3.75 3.75M21 12H3" />
                </svg>
                <code className={`font-mono truncate font-semibold ${item.confidence === "UNMAPPED" ? "text-slate-500" : "text-[#0C5ADB]"}`}>
                  {item.normalized}
                </code>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${CONFIDENCE_STYLES[item.confidence]} text-right whitespace-nowrap`}>
                  {item.confidence}
                </span>
              </div>
            ))}
          </div>

          {/* Footer note */}
          <div className="px-4 py-2 bg-slate-50 border-t border-slate-200">
            <p className="text-[10px] text-slate-500">
              Dataset type: <span className="text-slate-800 font-mono font-bold">{datasetType}</span>
              {" · "}Deterministic mapping
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
