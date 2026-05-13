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
  created_at: string;
  updated_at: string;
}

export interface TransactionCreatePayload {
  amount: string;
  date: string;
  category_id: number;
  description: string;
  is_recurring?: boolean;
}

export interface TransactionUpdatePayload {
  amount?: string;
  date?: string;
  category_id?: number;
  description?: string;
}

export interface BudgetRead {
  id: number;
  category_id: number;
  month: string;
  monthly_limit: string;
}

export interface BudgetSetPayload {
  month: string;
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
}

export interface ParsedRow {
  row_index: number;
  date: string | null;
  description: string;
  amount: string | null;
  kind_hint: "income" | "expense" | null;
  is_duplicate: boolean;
  errors: string[];
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
}
