import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { downloadBackup } from "@/api/backup";
import { useRestoreBackup } from "@/hooks/queries/useBackup";
import { HttpError } from "@/api/client";

export function BackupSection() {
  const [file, setFile] = useState<File | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const restore = useRestoreBackup();

  async function handleDownload() {
    try {
      await downloadBackup();
    } catch (err) {
      toast.error(err instanceof HttpError ? err.detail : "Download failed");
    }
  }

  function handleRestoreConfirm() {
    setConfirmOpen(false);
    if (file) restore.mutate(file);
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h4 className="text-sm font-medium">Download</h4>
        <p className="text-sm text-muted-foreground">
          Save a snapshot of your data as a SQLite file. Keep it somewhere safe.
        </p>
        <Button onClick={handleDownload}>Download backup</Button>
      </div>

      <div className="space-y-2 border-t pt-6">
        <h4 className="text-sm font-medium">Restore</h4>
        <p className="text-sm text-muted-foreground">
          Replace your current data with a previously-downloaded backup. The
          app will reload after the swap.
        </p>
        <div className="flex items-center gap-3">
          <Input
            type="file"
            accept=".db,application/octet-stream"
            aria-label="Backup file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            disabled={restore.isPending}
          />
          <Button
            variant="destructive"
            disabled={!file || restore.isPending}
            onClick={() => setConfirmOpen(true)}
          >
            {restore.isPending ? "Restoring…" : "Restore…"}
          </Button>
        </div>
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore from backup?</AlertDialogTitle>
            <AlertDialogDescription>
              This replaces all your current data with the contents of <b>{file?.name}</b>.
              The app will reload automatically. Your current state is archived first — the
              last 5 pre-restore archives are kept on disk.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRestoreConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Restore
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
