import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CsvHelpPanel } from "@/components/imports/CsvHelpPanel";
import { ImportConfigPanel } from "@/components/imports/ImportConfigPanel";
import { ImportPreviewTable } from "@/components/imports/ImportPreviewTable";
import {
  useCategories,
  useCreateCategory,
} from "@/hooks/queries/useCategories";
import { previewCsv, commitImport } from "@/api/csv-import";
import type {
  CsvImportConfig,
  ImportCommitRowSelection,
  ParsedRow,
} from "@/api/types";

const DEFAULT_CONFIG: CsvImportConfig = {
  delimiter: ";",
  decimal_sep: ".",
  thousands_sep: "",
  date_format: "%Y-%m-%d",
  skip_header_rows: 0,
  has_header: false,
  amount_format: "signed",
  sign_convention: "negative_is_expense",
  cols: { date: 0, description: 1, amount: 2 },
};

export default function ImportPage() {
  const { data: categories } = useCategories();
  const createCategory = useCreateCategory();

  const [fileContent, setFileContent] = useState<string | null>(null);
  const [config, setConfig] = useState<CsvImportConfig>(DEFAULT_CONFIG);
  const [rows, setRows] = useState<ParsedRow[] | null>(null);
  const [selections, setSelections] = useState<ImportCommitRowSelection[]>([]);
  const [committing, setCommitting] = useState(false);

  async function handleFile(f: File) {
    const text = await f.text();
    setFileContent(text);
    setRows(null);
  }

  async function ensureImportedCategory(): Promise<number> {
    const existing = (categories ?? []).find((c) => c.name === "Imported");
    if (existing) return existing.id;
    const created = await createCategory.mutateAsync({
      name: "Imported",
      kind: "expense",
    });
    return created.id;
  }

  async function handlePreview() {
    if (!fileContent) return;
    try {
      const r = await previewCsv(fileContent, config);
      setRows(r.rows);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Preview failed";
      toast.error(msg);
    }
  }

  async function handleCommit() {
    if (!fileContent || selections.length === 0) return;
    setCommitting(true);
    try {
      await ensureImportedCategory();
      const r = await commitImport(fileContent, config, selections);
      toast.success(`Imported ${r.imported}, skipped ${r.skipped}`);
      setRows(null);
      setFileContent(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Import failed";
      toast.error(msg);
    } finally {
      setCommitting(false);
    }
  }

  const importedCat = (categories ?? []).find((c) => c.name === "Imported");
  const defaultCategoryId = importedCat?.id ?? (categories ?? [])[0]?.id ?? 0;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Import</h2>

      <CsvHelpPanel />

      <Card>
        <CardHeader>
          <CardTitle>1. Upload</CardTitle>
        </CardHeader>
        <CardContent>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) =>
              e.target.files?.[0] && handleFile(e.target.files[0])
            }
          />
          {fileContent && (
            <p className="text-xs text-muted-foreground mt-2">
              Loaded {fileContent.split("\n").length} lines.
            </p>
          )}
        </CardContent>
      </Card>

      {fileContent && (
        <Card>
          <CardHeader>
            <CardTitle>2. Configure</CardTitle>
          </CardHeader>
          <CardContent>
            <ImportConfigPanel config={config} onChange={setConfig} />
            <div className="mt-4">
              <Button onClick={handlePreview}>Preview</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {rows && categories && (
        <Card>
          <CardHeader>
            <CardTitle>3. Review &amp; import</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ImportPreviewTable
              rows={rows}
              categories={categories}
              defaultCategoryId={defaultCategoryId}
              onSelectionsChange={setSelections}
            />
            <div className="flex items-center justify-between text-sm">
              <span>
                {selections.length} selected ·{" "}
                {rows.filter((r) => r.is_duplicate).length} duplicates ·{" "}
                {rows.filter((r) => r.errors.length > 0).length} errors
              </span>
              <Button
                onClick={handleCommit}
                disabled={selections.length === 0 || committing}
              >
                {committing ? "Importing…" : `Import ${selections.length}`}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
