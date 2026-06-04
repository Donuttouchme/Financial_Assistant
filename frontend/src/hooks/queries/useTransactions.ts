import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  createTransaction, deleteTransaction, listTransactions,
  searchTransactions, updateTransaction,
} from "@/api/transactions";
import type {
  Transaction, TransactionCreatePayload, TransactionUpdatePayload,
} from "@/api/types";
import { HttpError } from "@/api/client";

const TX_KEY_ROOT = "transactions";

export function useTransactions(
  params: { month?: string; category_id?: number },
  options?: { enabled?: boolean },
) {
  return useQuery<Transaction[]>({
    queryKey: [TX_KEY_ROOT, params.month ?? null, params.category_id ?? null],
    queryFn: () => listTransactions(params),
    enabled: options?.enabled ?? true,
  });
}

export function useSearchTransactions(
  q: string,
  options?: { enabled?: boolean },
) {
  return useQuery<Transaction[]>({
    queryKey: [TX_KEY_ROOT, "search", q],
    queryFn: () => searchTransactions(q),
    enabled: options?.enabled ?? true,
  });
}

function reportError(err: unknown) {
  toast.error(err instanceof HttpError ? err.detail : "Request failed");
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { payload: TransactionCreatePayload; silent?: boolean }) =>
      createTransaction(args.payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: [TX_KEY_ROOT] });
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      if (!vars.silent) toast.success("Transaction added");
    },
    onError: reportError,
  });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: number; payload: TransactionUpdatePayload }) =>
      updateTransaction(args.id, args.payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [TX_KEY_ROOT] });
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Transaction updated");
    },
    onError: reportError,
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteTransaction(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [TX_KEY_ROOT] });
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Transaction deleted");
    },
    onError: reportError,
  });
}
