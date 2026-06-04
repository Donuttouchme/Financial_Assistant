import { apiFetch } from "./client";
import type {
  Transaction,
  TransactionCreatePayload,
  TransactionUpdatePayload,
} from "./types";

export function listTransactions(params: {
  month?: string;
  category_id?: number;
}): Promise<Transaction[]> {
  const search = new URLSearchParams();
  if (params.month) search.set("month", params.month);
  if (params.category_id !== undefined) {
    search.set("category_id", String(params.category_id));
  }
  const qs = search.toString();
  return apiFetch<Transaction[]>(`/api/transactions${qs ? `?${qs}` : ""}`);
}

export function searchTransactions(q: string): Promise<Transaction[]> {
  const search = new URLSearchParams({ q });
  return apiFetch<Transaction[]>(`/api/transactions/search?${search.toString()}`);
}

export function createTransaction(
  payload: TransactionCreatePayload,
): Promise<Transaction> {
  return apiFetch<Transaction>("/api/transactions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateTransaction(
  id: number,
  payload: TransactionUpdatePayload,
): Promise<Transaction> {
  return apiFetch<Transaction>(`/api/transactions/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteTransaction(id: number): Promise<void> {
  return apiFetch<void>(`/api/transactions/${id}`, { method: "DELETE" });
}
