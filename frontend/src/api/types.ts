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
