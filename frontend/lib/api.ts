/**
 * API client for CASHpilot AI backend.
 * Base URL is configured via NEXT_PUBLIC_API_URL env var.
 */

import type {
  DemoLoadResponse,
  DemoStatusResponse,
  HealthResponse,
  UploadResponse,
  ImportListResponse,
  ReconRunResponse,
  ReconciliationSummaryResponse,
  PaginatedReconResults,
  DashboardOverviewResponse,
  PaginatedExceptions,
  ExceptionSummaryResponse,
  ExceptionDetail,
  FinancialExceptionItem,
  FinancialExceptionsSummary,
  PaginatedFinancialExceptions,
  ExceptionDetectionRunResponse,
  ExceptionStatusUpdateRequest,
  LineageGraphResponse,
  ForecastSummary,
  ForecastRunResponse,
  PaginatedForecasts,
  PaginatedAlerts,
  AlertsSummary,
  CashGapAlert,
  PaginatedAuditEvents,
  EvaluationMetrics,
} from "@/types";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");


async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let message = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      message = body?.detail ?? message;
    } catch {
      // keep the default message
    }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

/** GET /api/health */
export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health");
}

/** POST /api/demo/load — clear and reload demo data */
export async function loadDemoData(): Promise<DemoLoadResponse> {
  return apiFetch<DemoLoadResponse>("/api/demo/load", { method: "POST" });
}

/** GET /api/demo/status — current table row counts */
export async function getDemoStatus(): Promise<DemoStatusResponse> {
  return apiFetch<DemoStatusResponse>("/api/demo/status");
}

/**
 * POST /api/data/upload — upload one or more CSV files for validation.
 * Uses FormData so the browser sets the correct multipart boundary.
 */
export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file, file.name);
  }
  const res = await fetch(`${API_BASE}/api/data/upload`, {
    method: "POST",
    body: form,
    // DO NOT set Content-Type — browser must set it with the boundary
  });
  if (!res.ok) {
    let message = `Upload failed: ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      message = body?.detail ?? message;
    } catch { /* keep */ }
    throw new Error(message);
  }
  return res.json() as Promise<UploadResponse>;
}

/** GET /api/data/imports — list historical import records */
export async function getImports(
  limit = 20,
  offset = 0
): Promise<ImportListResponse> {
  return apiFetch<ImportListResponse>(
    `/api/data/imports?limit=${limit}&offset=${offset}`
  );
}

/** POST /api/reconciliation/run — trigger full reconciliation */
export async function runReconciliation(
  tolerancePaise = 1
): Promise<ReconRunResponse> {
  return apiFetch<ReconRunResponse>(
    `/api/reconciliation/run?tolerance_paise=${tolerancePaise}`,
    { method: "POST" }
  );
}

/** GET /api/reconciliation/summary — get reconciliation counters */
export async function getReconciliationSummary(): Promise<ReconciliationSummaryResponse> {
  return apiFetch<ReconciliationSummaryResponse>("/api/reconciliation/summary");
}

/** GET /api/reconciliation/orders-payments — paginated order-payment results */
export async function getOrderPaymentRecon(
  status?: string,
  search?: string,
  limit = 50,
  offset = 0
): Promise<PaginatedReconResults> {
  const params = new URLSearchParams();
  if (status && status !== "ALL") params.append("status", status);
  if (search && search.trim()) params.append("search", search.trim());
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());

  return apiFetch<PaginatedReconResults>(
    `/api/reconciliation/orders-payments?${params.toString()}`
  );
}

/** GET /api/reconciliation/settlements-bank — paginated settlement-bank results */
export async function getSettlementBankRecon(
  status?: string,
  search?: string,
  limit = 50,
  offset = 0
): Promise<PaginatedReconResults> {
  const params = new URLSearchParams();
  if (status && status !== "ALL") params.append("status", status);
  if (search && search.trim()) params.append("search", search.trim());
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());

  return apiFetch<PaginatedReconResults>(
    `/api/reconciliation/settlements-bank?${params.toString()}`
  );
}

/** GET /api/dashboard/overview — live KPI metrics from PostgreSQL */
export async function getDashboardOverview(): Promise<DashboardOverviewResponse> {
  return apiFetch<DashboardOverviewResponse>("/api/dashboard/overview");
}

/** GET /api/exceptions — paginated list of exceptions */
export async function getExceptions(
  severity?: string,
  exceptionType?: string,
  search?: string,
  limit = 25,
  offset = 0
): Promise<PaginatedExceptions> {
  const params = new URLSearchParams();
  if (severity && severity !== "ALL") params.append("severity", severity);
  if (exceptionType && exceptionType !== "ALL") params.append("exception_type", exceptionType);
  if (search && search.trim()) params.append("search", search.trim());
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());

  return apiFetch<PaginatedExceptions>(`/api/exceptions?${params.toString()}`);
}

/** GET /api/exceptions/summary — exception counters and value at risk */
export async function getExceptionSummary(): Promise<ExceptionSummaryResponse> {
  return apiFetch<ExceptionSummaryResponse>("/api/exceptions/summary");
}

/** GET /api/exceptions/{id} — full drill-down detail */
export async function getExceptionDetail(
  exceptionId: string | number
): Promise<ExceptionDetail> {
  return apiFetch<ExceptionDetail>(`/api/exceptions/${exceptionId}`);
}

// ─── Investigation & Lineage API ───────────────────────────────────────────

/** POST /api/exceptions/detect — run deterministic exception detection */
export async function runExceptionDetection(
  unfulfilledThresholdHours = 72,
  settlementWindowHours = 48,
  asOf?: string
): Promise<ExceptionDetectionRunResponse> {
  const params = new URLSearchParams();
  params.append("unfulfilled_threshold_hours", unfulfilledThresholdHours.toString());
  params.append("settlement_window_hours", settlementWindowHours.toString());
  if (asOf) params.append("as_of", asOf);

  return apiFetch<ExceptionDetectionRunResponse>(
    `/api/exceptions/detect?${params.toString()}`,
    { method: "POST" }
  );
}

/** GET /api/exceptions/cases — list investigation cases */
export async function getFinancialCases(
  exceptionType?: string,
  riskLevel?: string,
  status?: string,
  suggestedOwner?: string,
  search?: string,
  limit = 50,
  offset = 0
): Promise<PaginatedFinancialExceptions> {
  const params = new URLSearchParams();
  if (exceptionType && exceptionType !== "ALL") params.append("exception_type", exceptionType);
  if (riskLevel && riskLevel !== "ALL") params.append("risk_level", riskLevel);
  if (status && status !== "ALL") params.append("status", status);
  if (suggestedOwner && suggestedOwner !== "ALL") params.append("suggested_owner", suggestedOwner);
  if (search && search.trim()) params.append("search", search.trim());
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());

  return apiFetch<PaginatedFinancialExceptions>(
    `/api/exceptions/cases?${params.toString()}`
  );
}

/** GET /api/exceptions/cases/summary — KPI breakdown of investigation cases */
export async function getFinancialCasesSummary(): Promise<FinancialExceptionsSummary> {
  return apiFetch<FinancialExceptionsSummary>("/api/exceptions/cases/summary");
}

/** GET /api/exceptions/cases/{case_id} — full drill-down details */
export async function getFinancialCaseDetail(
  caseId: string
): Promise<FinancialExceptionItem> {
  return apiFetch<FinancialExceptionItem>(`/api/exceptions/cases/${caseId}`);
}

/** PATCH /api/exceptions/cases/{case_id}/status — update case status/assignee */
export async function updateFinancialCaseStatus(
  caseId: string,
  payload: ExceptionStatusUpdateRequest
): Promise<FinancialExceptionItem> {
  return apiFetch<FinancialExceptionItem>(
    `/api/exceptions/cases/${caseId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

/** GET /api/lineage/{entity_type}/{entity_id} — Money Lineage Graph */
export async function getMoneyLineage(
  entityType: string,
  entityId: string
): Promise<LineageGraphResponse> {
  return apiFetch<LineageGraphResponse>(
    `/api/lineage/${encodeURIComponent(entityType.toLowerCase())}/${encodeURIComponent(entityId)}`
  );
}

// ─── Forecast & Cash-Gap Alerts ────────────────────────────────────────────


/** POST /api/forecast/run — run forecast engine + gap detector */
export async function runForecastEngine(): Promise<ForecastRunResponse> {
  return apiFetch<ForecastRunResponse>("/api/forecast/run", { method: "POST" });
}

/** GET /api/forecast/summary — KPI summary split by horizon */
export async function getForecastSummary(): Promise<ForecastSummary> {
  return apiFetch<ForecastSummary>("/api/forecast/summary");
}

/** GET /api/forecast/upcoming — paginated pending/overdue forecasts */
export async function getForecastUpcoming(
  status?: string,
  limit = 50,
  offset = 0
): Promise<PaginatedForecasts> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());
  return apiFetch<PaginatedForecasts>(`/api/forecast/upcoming?${params.toString()}`);
}

/** GET /api/forecast/alerts/summary — alert KPI summary */
export async function getAlertsSummary(): Promise<AlertsSummary> {
  return apiFetch<AlertsSummary>("/api/forecast/alerts/summary");
}

/** GET /api/forecast/alerts — paginated cash-gap alerts */
export async function getCashGapAlerts(
  status?: string,
  severity?: string,
  alert_type?: string,
  limit = 50,
  offset = 0
): Promise<PaginatedAlerts> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (severity) params.append("severity", severity);
  if (alert_type) params.append("alert_type", alert_type);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());
  return apiFetch<PaginatedAlerts>(`/api/forecast/alerts?${params.toString()}`);
}

/** PATCH /api/forecast/alerts/{alert_id}/acknowledge */
export async function acknowledgeAlert(
  alertId: string,
  notes?: string
): Promise<CashGapAlert> {
  return apiFetch<CashGapAlert>(`/api/forecast/alerts/${alertId}/acknowledge`, {
    method: "PATCH",
    body: JSON.stringify({ notes: notes ?? null }),
  });
}

// ─── Audit Trail ─────────────────────────────────────────────────────────────

/** GET /api/audit/events — paginated audit trail events */
export async function getAuditEvents(
  entityType?: string,
  eventType?: string,
  limit = 50,
  offset = 0
): Promise<PaginatedAuditEvents> {
  const params = new URLSearchParams();
  if (entityType) params.append("entity_type", entityType);
  if (eventType) params.append("event_type", eventType);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());
  return apiFetch<PaginatedAuditEvents>(`/api/audit/events?${params.toString()}`);
}

/** GET /api/audit/events/{entity_id} — audit trail for a specific entity */
export async function getEntityAuditTrail(
  entityId: string,
  entityType?: string
): Promise<PaginatedAuditEvents> {
  const params = new URLSearchParams();
  if (entityType) params.append("entity_type", entityType);
  return apiFetch<PaginatedAuditEvents>(
    `/api/audit/events/${encodeURIComponent(entityId)}?${params.toString()}`
  );
}

// ─── Evaluation Dashboard ──────────────────────────────────────────────────

/** GET /api/evaluation/metrics — reconciliation & detection quality metrics */
export async function getEvaluationMetrics(): Promise<EvaluationMetrics> {
  return apiFetch<EvaluationMetrics>("/api/evaluation/metrics");
}
