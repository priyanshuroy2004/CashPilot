"use client";

import { useCallback, useRef, useState } from "react";

interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
  maxFileMB?: number;
}

export default function FileDropzone({
  onFilesSelected,
  disabled = false,
  maxFileMB = 50,
}: FileDropzoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (raw: FileList | null) => {
      if (!raw || disabled) return;
      const csvFiles = Array.from(raw).filter((f) =>
        f.name.toLowerCase().endsWith(".csv")
      );
      if (csvFiles.length) onFilesSelected(csvFiles);
    },
    [onFilesSelected, disabled]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`
        relative rounded-2xl border-2 border-dashed transition-all duration-200 cursor-pointer
        flex flex-col items-center justify-center gap-4 py-12 px-6 text-center
        ${disabled ? "opacity-50 cursor-not-allowed border-slate-300 bg-slate-100" :
          dragging
            ? "border-[#0C5ADB] bg-blue-50/50 scale-[1.01] shadow-md shadow-blue-500/10"
            : "border-slate-300 bg-slate-50/60 hover:border-[#0C5ADB] hover:bg-blue-50/20"
        }
      `}
    >
      {/* Animated upload icon */}
      <div className={`
        w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300
        ${dragging
          ? "bg-blue-100 scale-110"
          : "bg-white border border-slate-200 shadow-xs"
        }
      `}>
        <svg
          className="w-8 h-8 transition-colors duration-200 text-[#0C5ADB]"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
      </div>

      <div>
        <p className={`text-base font-bold mb-1 transition-colors duration-200 ${dragging ? "text-[#0C5ADB]" : "text-slate-900"}`}>
          {dragging ? "Drop CSV files here" : "Drag & drop CSV files"}
        </p>
        <p className="text-sm text-slate-500 font-medium">or click to browse from device</p>
      </div>

      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
        disabled={disabled}
        className="px-5 py-2.5 rounded-xl bg-[#0C5ADB] hover:bg-[#0944A8] text-white text-xs font-bold shadow-xs transition-all duration-200 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      >
        Select Files
      </button>

      <p className="text-xs text-slate-500 font-medium">
        .csv only · max {maxFileMB} MB per file · multiple files supported
      </p>

      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
        disabled={disabled}
      />

      {/* Drag overlay highlight */}
      {dragging && (
        <div className="absolute inset-0 rounded-2xl border-2 border-[#0C5ADB] animate-pulse pointer-events-none" />
      )}
    </div>
  );
}
