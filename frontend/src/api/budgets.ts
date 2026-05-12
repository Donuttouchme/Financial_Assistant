import { apiFetch } from "./client";
import type { BudgetRead, BudgetSetPayload, BudgetWithSpending } from "./types";

export function listBudgetsWithSpending(month: string): Promise<BudgetWithSpending[]> {
  return apiFetch<BudgetWithSpending[]>(
    `/api/budgets?month=${encodeURIComponent(month)}`,
  );
}

export function setBudget(
  categoryId: number,
  payload: BudgetSetPayload,
): Promise<BudgetRead> {
  return apiFetch<BudgetRead>(`/api/budgets/${categoryId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
