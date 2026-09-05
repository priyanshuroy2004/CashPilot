/**
 * TypeScript types for CASHpilot AI frontend.
 */

// ─── API Response Types ──────────────────────────────────────────────────────

export interface HealthResponse {
  status: "ok" | "degraded";
  database: "connected" | "unreachable";
  version: string;
}

export interface DemoLoadResponse {
  success: boolean;
  message: string;
  orders: number;
  payments: number;
  settlements: number;
  settlement_lines: number;
  bank_transactions: number;
}

export interface DemoStatusResponse {
  orders: number;
  payments: number;
  settlements: number;
  settlement_lines: number;
  bank_transactions: number;
  reconciliation_results: number;
  data_imports: number;
}

// ─── Navigation ──────────────────────────────────────────────────────────────

export interface NavItem {
  label: string;
  href: string;
  icon: string;
  badge?: string;
}

// ─── Upload / Validation Types ───────────────────────────────────────────────

export interface ColumnMappingItem {
  original: string;
  normalized: string;
  confidence: "HIGH" | "MEDIUM" | "UNMAPPED";
}

export interface ValidationError {
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

export interface UploadResponse {
  files: FileUploadResult[];
}

export interface CommitResponse {
  session_id: string;
  dataset_type: string;
  imported: number;
  skipped: number;
  data_import_id: number;
  message: string;
}

export interface ImportListItem {
  id: number;
  filename: string;
  dataset_type: string;
  row_count: number | null;
  status: string;
  error_count: number;
  created_at: string;
}

export interface ImportListResponse {
  imports: ImportListItem[];
  total: number;
}

// ─── Reconciliation Types ───────────────────────────────────────────────────

export interface ReconciliationItem {
  id: number;
  entity_type: "ORDER" | "PAYMENT" | "SETTLEMENT" | "BANK_TRANSACTION";
  entity_id: string;
  related_entity_id: string | null;
  match_type: string | null;
  status: string;
  confidence: number | null;
  expected_amount: number | null; // paise
  actual_amount: number | null;   // paise
  difference: number | null;      // paise
  reason: string | null;
  created_at: string | null;
}

export interface OrdersPaymentsSummary {
  matched: number;
  amount_mismatch: number;
  payment_missing: number;
  order_missing: number;
  failed: number;
  needs_review: number;
  total: number;
}

export interface SettlementsBankSummary {
  matched: number;
  pending: number;
  mismatch: number;
  needs_review: number;
  total: number;
}

export interface ReconciliationSummaryResponse {
  orders_payments: OrdersPaymentsSummary;
  settlements_bank: SettlementsBankSummary;
  total_records: number;
}

export interface ReconRunResponse {
  success: boolean;
  message: string;
  orders_payments: OrdersPaymentsSummary;
  settlements_bank: SettlementsBankSummary;
  total_records: number;
}

export interface PaginatedReconResults {
  items: ReconciliationItem[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Dashboard Overview Types ───────────────────────────────────────────────

export interface DashboardOverviewResponse {
  has_data: boolean;
  total_orders: number;
  total_orders_amount: number; // paise
  total_captured_payments: number;
  total_captured_amount: number; // paise
  total_settlements: number;
  total_settlements_net: number; // paise
  total_bank_credits: number;
  total_bank_credits_amount: number; // paise
  matched_records: number;
  pending_missing_records: number;
  exception_count: number;
  value_at_risk: number; // paise
  orders_payments: {
    matched: number;
    amount_mismatch: number;
    payment_missing: number;
    order_missing: number;
    failed: number;
    needs_review: number;
    total: number;
  };
  settlements_bank: {
    matched: number;
    pending: number;
    mismatch: number;
    needs_review: number;
    total: number;
  };
}

// ─── Exceptions Workspace Types ─────────────────────────────────────────────

export interface MatchingMethodCheck {
  method: string;
  attempted: boolean;
  passed: boolean;
  details?: string | null;
}

export interface ExceptionItem {
  id: number;
  exception_id: string;
  exception_type: string;
  entity_type: string;
  entity_id: string;
  related_entity_id?: string | null;
  amount_at_risk: number; // paise
  severity: "HIGH" | "MEDIUM" | "LOW";
  status: string;
  match_type?: string | null;
  confidence?: number | null;
  expected_amount?: number | null;
  actual_amount?: number | null;
  difference?: number | null;
  reason?: string | null;
  created_at?: string | null;
  methods_attempted: MatchingMethodCheck[];
  recommended_action?: string | null;
}

export interface ExceptionSummaryResponse {
  total_exceptions: number;
  high_severity: number;
  medium_severity: number;
  low_severity: number;
  total_value_at_risk: number; // paise
  by_type: Record<string, number>;
}

export interface PaginatedExceptions {
  total: number;
  items: ExceptionItem[];
  limit: number;
  offset: number;
}

export type ExceptionDetail = ExceptionItem;

// ─── Investigation & Lineage Types ───────────────────────────────────────────

export interface FinancialExceptionItem {
  id: number;
  case_id: string;
  exception_type: string;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  value_at_risk: number; // paise
  value_at_risk_inr: string;
  status: "OPEN" | "ASSIGNED" | "IN_REVIEW" | "RESOLVED" | "DISMISSED" | "ESCALATED";
  suggested_owner: "Finance" | "Operations" | "Support" | string;
  related_order_id?: string | null;
  related_payment_id?: string | null;
  related_settlement_id?: string | null;
  related_bank_entry_id?: string | null;
  evidence: Record<string, any>;
  explanation: string;
  triggering_rule: string;
  detected_at: string;
  updated_at: string;
  assignee?: string | null;
  resolution_notes?: string | null;
}

export interface FinancialExceptionsSummary {
  total_cases: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_value_at_risk_paise: number;
  total_value_at_risk_inr: string;
  by_type: Record<string, number>;
  by_owner: Record<string, number>;
  by_status: Record<string, number>;
}

export interface PaginatedFinancialExceptions {
  total: number;
  items: FinancialExceptionItem[];
  limit: number;
  offset: number;
}

export interface ExceptionDetectionRunResponse {
  success: boolean;
  message: string;
  total_exceptions: number;
  total_value_at_risk_paise: number;
  total_value_at_risk_inr: string;
  by_type: Record<string, number>;
  by_risk: Record<string, number>;
  unfulfilled_detected: number;
  settlement_missing_detected: number;
  other_anomalies_detected: number;
}

export interface ExceptionStatusUpdateRequest {
  status: string;
  assignee?: string | null;
  resolution_notes?: string | null;
}

export interface LineageNodeData extends Record<string, any> {
  category:
    | "ORDER"
    | "PAYMENT"
    | "SETTLEMENT"
    | "BANK_CREDIT"
    | "LEDGER"
    | "SHIPMENT"
    | "REFUND"
    | "EXCEPTION"
    | "FEE"
    | "TAX";
  title: string;
  source_system: string;
  record_id: string;
  amount_paise?: number | null;
  amount_inr?: string | null;
  date?: string | null;
  status: string;
  status_label: string;
  visual_status: "green" | "yellow" | "red" | "grey" | "blue";
  is_missing: boolean;
  confidence?: number | null;
  rule?: string | null;
  discrepancy?: string | null;
  details?: Record<string, any>;
  related_records?: string[];
}

export interface LineageNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: LineageNodeData;
}

export interface LineageEdge {
  id: string;
  source: string;
  target: string;
  label?: string | null;
  animated?: boolean;
  style?: Record<string, any>;
}

export interface LineageGraphSummary {
  complete: boolean;
  total_nodes: number;
  total_edges: number;
  status: string;
  gross_amount_paise: number;
  gross_amount_inr: string;
  net_settled_inr: string;
  break_point?: string | null;
}

export interface LineageGraphResponse {
  root_entity: {
    type: string;
    id: string;
  };
  summary: LineageGraphSummary;
  nodes: LineageNode[];
  edges: LineageEdge[];
}

// ─── Forecast & Cash-Gap Alerts ──────────────────────────────────────────────

export interface HorizonSummary {
  horizon_days: number;
  payment_count: number;
  expected_amount_paise: number;
  expected_amount_inr: string;
}

export interface ForecastSummary {
  label: string;
  horizon_1_day: HorizonSummary;
  horizon_3_days: HorizonSummary;
  horizon_7_days: HorizonSummary;
  horizon_14_days: HorizonSummary;
  total_overdue_count: number;
  total_overdue_paise: number;
  total_overdue_inr: string;
  pending_count: number;
  pending_paise: number;
  pending_inr: string;
}

export interface ForecastRecord {
  id: number;
  forecast_id: string;
  payment_id: string;
  order_id: string | null;
  settlement_id: string | null;
  expected_amount_paise: number;
  expected_amount_inr: string;
  horizon_days: number;
  expected_settlement_date: string;
  basis: string;
  status: "PENDING" | "SETTLED" | "OVERDUE" | "CANCELLED";
  payment_captured_at: string | null;
  gateway: string | null;
  created_at: string;
}

export interface PaginatedForecasts {
  total: number;
  items: ForecastRecord[];
  limit: number;
  offset: number;
}

export interface ForecastRunResponse {
  success: boolean;
  message: string;
  unsettled_payments_count: number;
  forecasts_created: number;
  horizon_summary: Record<string, {
    horizon_days: number;
    payment_count: number;
    expected_amount_paise: number;
    expected_amount_inr: string;
  }>;
  gap_detection?: {
    alerts_created: number;
    alerts_updated: number;
    total_open_alerts: number;
    total_risk_paise: number;
    total_risk_inr: string;
  } | null;
}

export interface CashGapAlert {
  id: number;
  alert_id: string;
  alert_type: "SETTLEMENT_DELAY" | "RISK_GAP" | "OVERDUE_SETTLEMENT";
  payment_id: string | null;
  settlement_id: string | null;
  order_id: string | null;
  expected_date: string | null;
  actual_date: string | null;
  gap_days: number;
  gap_amount_paise: number;
  gap_amount_inr: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedAlerts {
  total: number;
  items: CashGapAlert[];
  limit: number;
  offset: number;
}

export interface AlertsSummary {
  total_open: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_risk_paise: number;
  total_risk_inr: string;
  by_type: Record<string, number>;
}

// ─── Audit Trail ─────────────────────────────────────────────────────────────

export interface AuditEvent {
  id: number;
  event_id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor: string;
  from_value: Record<string, unknown> | null;
  to_value: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
}

export interface PaginatedAuditEvents {
  total: number;
  items: AuditEvent[];
  limit: number;
  offset: number;
}

// ─── Evaluation Metrics ──────────────────────────────────────────────────────

export interface EvaluationMetrics {
  generated_at: string;
  note: string;
  reconciliation: { total_records: number; matched: number; accuracy_pct: number; };
  settlement_calculations: { total: number; correct: number; discrepancy: number; accuracy_pct: number; discrepancy_rate_pct: number; };
  refund_reconciliation: { total: number; matched: number; accuracy_pct: number; by_status: Record<string, number>; };
  tax_reconciliation: { total: number; matched: number; accuracy_pct: number; };
  exception_detection: { total_orders: number; total_exceptions: number; detection_rate_pct: number; by_type: Record<string, number>; };
  resolution_performance: { resolved_cases: number; avg_resolution_hours: number | null; total_open_cases: number; open_by_risk: Record<string, number>; status_distribution: Record<string, number>; };
  audit_trail: { total_events: number; by_event_type: Record<string, number>; };
  payment_posture: { total_captured_payments: number; };
  ground_truth: { note: string; available: boolean; };
}
