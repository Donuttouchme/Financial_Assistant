import { HttpError } from "./client";

export async function downloadBackup(): Promise<void> {
  const res = await fetch("/api/backup/download");
  if (!res.ok) {
    let detail = res.statusText || "Download failed";
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      /* body not JSON */
    }
    throw new HttpError(res.status, detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `financial-${new Date().toISOString().slice(0, 10)}.db`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function uploadRestore(file: File): Promise<void> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/backup/restore", { method: "POST", body: fd });
  if (!res.ok) {
    let detail = res.statusText || "Restore failed";
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      /* body not JSON */
    }
    throw new HttpError(res.status, detail);
  }
}
