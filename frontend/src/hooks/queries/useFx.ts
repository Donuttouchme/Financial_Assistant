import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getFxStatus, refreshFx } from "@/api/fx";
import { HttpError } from "@/api/client";

const KEY = ["fx", "status"];

export function useFxStatus() {
  return useQuery({ queryKey: KEY, queryFn: getFxStatus });
}

export function useRefreshFx() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: refreshFx,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["budgets"] });
      if (data.ok) toast.success(`Rates refreshed (${data.currencies_updated} currencies)`);
      else toast.error("Rate refresh failed — check your connection");
    },
    onError: (err) => {
      toast.error(err instanceof HttpError ? err.detail : "Refresh failed");
    },
  });
}
