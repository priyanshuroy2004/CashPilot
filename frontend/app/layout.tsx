import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CASHpilot AI — Finance Dashboard & Reconciliation Engine",
  description:
    "CASHpilot AI: Advanced Financial Control Dashboard + Multi-way Reconciliation Engine for high-volume e-commerce merchants. Detect cash leaks, reconcile payouts, and automate exception audits.",
  keywords: ["finance", "reconciliation", "payments", "e-commerce", "cash management", "audit", "razorpay"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-[#F8FAFC] text-slate-900 min-h-screen selection:bg-[#0C5ADB]/20 selection:text-[#0C5ADB]`}
      >
        <div className="min-h-screen flex flex-col lg:flex-row">
          <Sidebar />
          <main className="flex-1 min-w-0 overflow-x-hidden bg-[#F8FAFC]">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
