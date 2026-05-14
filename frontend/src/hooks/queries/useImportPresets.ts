import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createImportPreset,
  deleteImportPreset,
  listImportPresets,
  updateImportPreset,
} from "@/api/import-presets";
import type { ImportPresetCreatePayload } from "@/api/types";

const KEY = ["import-presets"] as const;

export function useImportPresets() {
  return useQuery({ queryKey: KEY, queryFn: listImportPresets });
}

export function useCreateImportPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: ImportPresetCreatePayload) => createImportPreset(p),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateImportPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: ImportPresetCreatePayload;
    }) => updateImportPreset(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteImportPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteImportPreset(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
