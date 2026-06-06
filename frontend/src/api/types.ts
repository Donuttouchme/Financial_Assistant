export type CategoryKind = "income" | "expense" | "savings";

export interface Category {
  id: number;
  name: string;
  kind: CategoryKind;
  target_amount: string | null;
  target_date: string | null;  // ISO YYYY-MM-DD
  created_at: string;
}

export interface CategoryCreatePayload {
  name: string;
  kind?: CategoryKind;
  target_amount?: string | null;
  target_date?: string | null;
}

export interface Transaction {
  id: number;
  user_id: number;
  amount: string;
  date: string;
  category_id: number;
  description: string;
  is_recurring: boolean;
  currency: string;
  base_amount: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionCreatePayload {
  amount: string;
  date: string;
  category_id: number;
  description: string;
  is_recurring?: boolean;
  currency?: string;
}

export interface TransactionUpdatePayload {
  amount?: string;
  date?: string;
  category_id?: number;
  description?: string;
  currency?: string;
}

export interface BudgetRead {
  id: number;
  category_id: number;
  month: string;
  monthly_limit: string;
}

export interface BudgetSetPayload {
  /** Effective-from month is server-stamped; client only sends the limit. */
  monthly_limit: string;
}

export interface BudgetWithSpending {
  category_id: number;
  category_name: string;
  month: string;
  monthly_limit: string;
  spent: string;
  over_budget: boolean;
  overage: string;
}

export interface ApiError {
  detail: string;
  status: number;
}

export type AmountFormat = "signed" | "debit_credit";
export type SignConvention = "negative_is_expense" | "negative_is_income";

export interface CsvColumnMapping {
  date: number;
  description: number;
  amount?: number | null;
  debit?: number | null;
  credit?: number | null;
  currency?: number | null;
}

export interface CsvImportConfig {
  delimiter: string;
  decimal_sep: string;
  thousands_sep: string;
  date_format: string;
  skip_header_rows: number;
  has_header: boolean;
  amount_format: AmountFormat;
  sign_convention: SignConvention;
  cols: CsvColumnMapping;
  default_currency?: string | null;
}

export interface ParsedRow {
  row_index: number;
  date: string | null;
  description: string;
  amount: string | null;
  currency: string | null;
  kind_hint: "income" | "expense" | null;
  is_duplicate: boolean;
  errors: string[];
}

export interface SettingsRead {
  base_currency: string;
}

export interface BaseCurrencyChangePreviewRow {
  category_id: number;
  category_name: string;
  month?: string;
  old_amount: string;
  new_amount: string;
}

export interface BaseCurrencyChangePreview {
  old_base: string;
  new_base: string;
  budgets: BaseCurrencyChangePreviewRow[];
  savings_goals: BaseCurrencyChangePreviewRow[];
}

export interface FxStatusRead {
  latest_date: string | null;
  source: string;
  is_fresh: boolean;
}

export interface FxRefreshResponse {
  fetched_date: string | null;
  currencies_updated: number;
  ok: boolean;
}

export interface RecurringSchedule {
  id: number;
  transaction_id: number;
  amount: string;
  category_id: number;
  description: string;
  currency: string;
  start_date: string;
  next_occurrence_date: string;
  frequency: string;
}

export interface RecurringUpdate {
  amount?: string;
  category_id?: number;
  description?: string;
  currency?: string;
  frequency?: string;
}

export interface ImportPreset {
  id: number;
  name: string;
  config: CsvImportConfig;
  created_at: string;
  updated_at: string;
}

export interface ImportPresetCreatePayload {
  name: string;
  config: CsvImportConfig;
}

export interface ImportCommitRowSelection {
  row_index: number;
  category_id: number;
  is_recurring: boolean;
}

export interface ImportCommitResponse {
  imported: number;
  skipped: number;
  // ISO date strings for which FX rates could not be fetched at commit time.
  // Populated from the X-Fx-Missing-Dates response header; empty when
  // frankfurter delivered everything. Affected transactions land with
  // base_amount=null and self-correct on the next FX refresh.
  missing_fx_dates: string[];
}

// ---------- Forecast ----------

export interface DailyPoint {
  date: string; // ISO YYYY-MM-DD
  cumulative: string; // Decimal string
  is_forecast: boolean;
}

export interface DailyCumulativeResponse {
  month: string;
  base_currency: string;
  today: string;
  forecast_available: boolean;
  points: DailyPoint[];
}

export type BucketKind = "past" | "current" | "future";

export interface MonthlyPoint {
  month: string;
  total: string;
  actual_mtd: string | null;
  forecast_remainder: string | null;
  kind: BucketKind;
}

export type ForecastHorizon = "1m" | "3m" | "6m" | "1y" | "2y";
export type ForecastMode = "centered" | "forward";

export interface MonthlyBucketsResponse {
  horizon: ForecastHorizon;
  mode: ForecastMode;
  base_currency: string;
  today: string;
  forecast_available: boolean;
  points: MonthlyPoint[];
}
