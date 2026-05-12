import { apiFetch } from "./client";
import type { Category, CategoryCreatePayload } from "./types";

export function listCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/api/categories");
}

export function createCategory(payload: CategoryCreatePayload): Promise<Category> {
  return apiFetch<Category>("/api/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteCategory(id: number): Promise<void> {
  return apiFetch<void>(`/api/categories/${id}`, { method: "DELETE" });
}
