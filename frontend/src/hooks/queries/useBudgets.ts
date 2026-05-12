import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  listBudgetsWithSpending, setBudget,
} from "@/api/budgets";
import type { BudgetWithSpending, BudgetSetPayload } from "@/api/types";
import { HttpError } from "@/api/client";

export function useBudgetsForMonth(month: string) {
  return useQuery<BudgetWithSpending[]>({
    queryKey: ["budgets", month],
    queryFn: () => listBudgetsWithSpending(month),
  });
}

export function useSetBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { categoryId: number; payload: BudgetSetPayload }) =>
      setBudget(args.categoryId, args.payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["budgets"] });
      toast.success("Budget updated");
    },
    onError: (err) =>
      toast.error(err instanceof HttpError ? err.detail : "Failed to set budget"),
  });
}
