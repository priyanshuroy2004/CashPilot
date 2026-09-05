"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState, useEffect } from "react";

interface NavItem {
  label: string;
  href: string;
  icon: (active: boolean) => React.ReactNode;
  badge?: string;
  badgeColor?: string;
}

const navItems: NavItem[] = [
  {
    label: "Overview",
    href: "/",
    icon: (active) => (
      <svg className={`w-5 h-5 transition-colors ${active ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.75} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
      </svg>
    ),
  },
  {
    label: "Reconciliation",
    href: "/reconciliation",
    icon: (active) => (
      <svg className={`w-5 h-5 transition-colors ${active ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.75} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
    badge: "Live",
    badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-400/30",
  },
  {
    label: "Exceptions",
    href: "/exceptions",
    icon: (active) => (
      <svg className={`w-5 h-5 transition-colors ${active ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.75} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    ),
    badge: "Audit",
    badgeColor: "bg-amber-500/20 text-amber-300 border-amber-400/30",
  },
  {
    label: "Financial",
    href: "/financial",
    icon: (active) => (
      <svg className={`w-5 h-5 transition-colors ${active ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.75} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    label: "Data Import",
    href: "/data",
    icon: (active) => (
      <svg className={`w-5 h-5 transition-colors ${active ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.75} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
      </svg>
    ),
  },
  {
    label: "Forecast & Alerts",
    href: "/forecast",
    icon: (active) => (
      <svg className={`w-5 h-5 transition-colors ${active ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.75} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
      </svg>
    ),
  },
  {
    label: "Evaluation",
    href: "/evaluation",
    icon: (active) => (
      <svg className={`w-5 h-5 transition-colors ${active ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.75} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Close mobile drawer when route changes
  useEffect(() => {
    setIsMobileOpen(false);
  }, [pathname]);

  // Prevent scroll when mobile drawer is open
  useEffect(() => {
    if (isMobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isMobileOpen]);

  return (
    <>
      {/* ─── Mobile Top Header Bar (< 1024px) ──────────────────────────────── */}
      <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between px-4 py-3 bg-[#0C2340] text-white border-b border-white/[0.08] shadow-md">
        <Link href="/" className="block">
          <span className="font-bold text-base tracking-tight text-white block">CASHpilot AI</span>
          <span className="text-[10px] uppercase tracking-wider text-blue-300 font-medium block">Finance Controller</span>
        </Link>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/30 text-[10px] text-emerald-300 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00B574] animate-pulse" />
            <span>Audit Live</span>
          </div>

          <button
            onClick={() => setIsMobileOpen(true)}
            aria-label="Open Navigation Menu"
            className="p-2 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] border border-white/[0.1] text-white transition cursor-pointer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
        </div>
      </header>

      {/* ─── Mobile Drawer Backdrop ────────────────────────────────────────── */}
      {isMobileOpen && (
        <div
          onClick={() => setIsMobileOpen(false)}
          className="lg:hidden fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm transition-opacity duration-300 animate-fadeIn"
        />
      )}

      {/* ─── Mobile Slide-out Navigation Drawer ─────────────────────────────── */}
      <aside
        className={`lg:hidden fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-[#0C2340] text-white border-r border-white/[0.1] shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Drawer Header */}
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
          <div>
            <span className="font-bold text-base tracking-tight text-white block">CASHpilot AI</span>
            <span className="text-[10px] uppercase tracking-wider text-blue-300 font-medium block">Finance Controller</span>
          </div>

          <button
            onClick={() => setIsMobileOpen(false)}
            aria-label="Close navigation"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition cursor-pointer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Drawer Nav Links */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsMobileOpen(false)}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                  isActive
                    ? "bg-[#0C5ADB] text-white shadow-md shadow-blue-950/40 font-semibold"
                    : "text-slate-300 hover:text-white hover:bg-white/[0.06]"
                }`}
              >
                <div className="flex items-center gap-3">
                  {item.icon(isActive)}
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${item.badgeColor}`}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-white/[0.08] bg-[#08162B]">
          <div className="flex items-center gap-2 text-xs text-slate-300">
            <span className="w-2 h-2 rounded-full bg-[#00B574] animate-pulse" />
            <span className="font-semibold text-white">Deterministic Guardrails</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">v4.2.0 • Financial Recon Engine</p>
        </div>
      </aside>

      {/* ─── Desktop Pinned Sidebar (>= 1024px) ────────────────────────────── */}
      <aside className="hidden lg:flex w-64 shrink-0 h-screen sticky top-0 bg-[#0C2340] border-r border-slate-800/80 flex-col z-20 select-none shadow-xl shadow-slate-900/10">
        {/* Brand Header */}
        <div className="px-5 py-5 border-b border-white/[0.08]">
          <Link href="/" className="block group">
            <h1 className="text-lg font-bold text-white tracking-tight">
              CASHpilot AI
            </h1>
            <p className="text-[10px] text-blue-300 font-semibold uppercase tracking-wider mt-0.5">
              Finance Controller
            </p>
          </Link>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 px-3 py-5 space-y-1 overflow-y-auto">
          <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Financial Suite
          </div>
          {navItems.map((item) => {
            const isActive =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  relative flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium
                  transition-all duration-150 group
                  ${
                    isActive
                      ? "bg-[#0C5ADB] text-white font-semibold shadow-md shadow-blue-950/40"
                      : "text-slate-300 hover:text-white hover:bg-white/[0.06]"
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  {item.icon(isActive)}
                  <span className="tracking-wide">{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${item.badgeColor}`}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Live Engine Guardrails Footer */}
        <div className="p-4 m-3 rounded-xl bg-[#08162B] border border-white/[0.08] shadow-inner">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00B574] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00B574]" />
            </span>
            <span className="text-xs font-semibold text-white">Zero-Loss Guardrails</span>
          </div>
          <p className="text-[10px] text-slate-300 mt-1 leading-relaxed">
            Deterministic 1-paise tolerance reconciliation active across all payment & bank ledgers.
          </p>
          <div className="mt-2.5 pt-2 border-t border-white/[0.08] flex items-center justify-between text-[10px] text-slate-400 font-mono">
            <span>Core v4.2</span>
            <span className="text-emerald-400 font-semibold">Protected</span>
          </div>
        </div>
      </aside>
    </>
  );
}
