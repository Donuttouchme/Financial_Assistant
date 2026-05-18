import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  getSettings,
  previewBaseCurrencyChange,
  updateBaseCurrency,
} from "@/api/settings";
import { HttpError } from "@/api/client";

const KEY = ["settings"];

export function useSettings() {
  return useQuery({ queryKey: KEY, queryFn: getSettings });
}

/** The current base currency, or "CHF" while settings are loading. */
export function useBaseCurrency(): string {
  const { data } = useSettings();
  return data?.base_currency ?? "CHF";
}

export function useUpdateBaseCurrency() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => updateBaseCurrency(code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["categories"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Base currency updated");
    },
    onError: (err) => {
      toast.error(err instanceof HttpError ? err.detail : "Update failed");
    },
  });
}

export function usePreviewBaseCurrencyChange() {
  return useMutation({
    mutationFn: (code: string) => previewBaseCurrencyChange(code),
    onError: (err) => {
      toast.error(err instanceof HttpError ? err.detail : "Preview failed");
    },
  });
}
