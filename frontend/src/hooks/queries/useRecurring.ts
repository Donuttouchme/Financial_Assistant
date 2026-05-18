import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  deleteRecurring,
  listRecurring,
  updateRecurring,
} from "@/api/recurring";
import type { RecurringSchedule, RecurringUpdate } from "@/api/types";
import { HttpError } from "@/api/client";

const KEY = ["recurring"] as const;

export function useRecurring() {
  return useQuery<RecurringSchedule[]>({ queryKey: KEY, queryFn: listRecurring });
}

export function useUpdateRecurring() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: RecurringUpdate }) =>
      updateRecurring(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Schedule updated");
    },
    onError: (err) =>
      toast.error(err instanceof HttpError ? err.detail : "Update failed"),
  });
}

export function useDeleteRecurring() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteRecurring(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Schedule deleted");
    },
    onError: (err) =>
      toast.error(err instanceof HttpError ? err.detail : "Delete failed"),
  });
}
