import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { uploadRestore } from "@/api/backup";
import { HttpError } from "@/api/client";

// Give the backend ~2s to flush the 202 response, exit(75) in its daemon
// thread, and let RUN.bat relaunch uvicorn before the browser reloads.
const RELOAD_DELAY_MS = 2000;

export function useRestoreBackup() {
  return useMutation({
    mutationFn: uploadRestore,
    onSuccess: () => {
      toast.success("Restore staged. Reloading…");
      window.setTimeout(() => window.location.reload(), RELOAD_DELAY_MS);
    },
    onError: (err) => {
      toast.error(err instanceof HttpError ? err.detail : "Restore failed");
    },
  });
}
