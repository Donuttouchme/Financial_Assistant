import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  createCategory, deleteCategory, listCategories,
} from "@/api/categories";
import type { Category, CategoryCreatePayload } from "@/api/types";
import { HttpError } from "@/api/client";

const KEY = ["categories"] as const;

export function useCategories() {
  return useQuery<Category[]>({ queryKey: KEY, queryFn: listCategories });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CategoryCreatePayload) => createCategory(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      toast.success("Category created");
    },
    onError: (err) =>
      toast.error(err instanceof HttpError ? err.detail : "Failed to create"),
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Category deleted");
    },
    onError: (err) =>
      toast.error(err instanceof HttpError ? err.detail : "Failed to delete"),
  });
}
