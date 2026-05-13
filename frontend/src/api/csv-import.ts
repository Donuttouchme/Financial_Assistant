import { apiFetch } from "./client";
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

export function commitImport(
  fileContent: string,
  config: CsvImportConfig,
  selections: ImportCommitRowSelection[],
): Promise<ImportCommitResponse> {
  return apiFetch<ImportCommitResponse>("/api/import/commit", {
    method: "POST",
    body: JSON.stringify({ file_content: fileContent, config, selections }),
  });
}
