import { apiFetch, HttpError } from "./client";
import type {
  CsvImportConfig,
  ImportCommitResponse,
  ImportCommitRowSelection,
  ParsedRow,
} from "./types";

export function previewCsv(
  fileContent: string,
  config: CsvImportConfig,
): Promise<{ rows: ParsedRow[] }> {
  return apiFetch<{ rows: ParsedRow[] }>("/api/import/preview", {
    method: "POST",
    body: JSON.stringify({ file_content: fileContent, config }),
  });
}

export async function commitImport(
  fileContent: string,
  config: CsvImportConfig,
  selections: ImportCommitRowSelection[],
): Promise<ImportCommitResponse> {
  // Manual fetch (not apiFetch) so we can read the X-Fx-Missing-Dates header
  // that the backend sets when frankfurter couldn't deliver rates for some
  // transaction dates. The affected rows still land successfully but with
  // base_amount=null until the next FX refresh.
  const res = await fetch("/api/import/commit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_content: fileContent,
      config,
      selections,
      default_currency: config.default_currency ?? null,
    }),
  });
  if (!res.ok) {
    let detail = res.statusText || "Import failed";
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      /* body not JSON */
    }
    throw new HttpError(res.status, detail);
  }
  const body = (await res.json()) as Omit<ImportCommitResponse, "missing_fx_dates">;
  const missingHeader = res.headers.get("X-Fx-Missing-Dates");
  const missing_fx_dates =
    missingHeader && missingHeader.length > 0 ? missingHeader.split(",") : [];
  return { ...body, missing_fx_dates };
}
