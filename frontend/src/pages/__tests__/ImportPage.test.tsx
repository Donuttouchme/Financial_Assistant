import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import ImportPage from "@/pages/ImportPage";
import { resetTestState, testState } from "@/tests/handlers";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  );
}

function wrapWithSpy(node: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const spy = vi.spyOn(qc, "invalidateQueries");
  const tree = (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  );
  return { tree, spy };
}

beforeEach(() => resetTestState());

/** jsdom's File does not implement Blob.text(); polyfill it for tests. */
function makeCsvFile(content: string, name = "test.csv"): File {
  const file = new File([content], name, { type: "text/csv" });
  // jsdom doesn't implement Blob.text() — add it manually
  Object.defineProperty(file, "text", {
    value: () => Promise.resolve(content),
    writable: false,
  });
  return file;
}

describe("ImportPage — currency UI", () => {
  async function showConfigPanel() {
    const csvContent = "date;description;amount\n2026-01-01;Test;-10";
    const file = makeCsvFile(csvContent);
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    await userEvent.upload(input, file);
  }

  it("renders Default currency picker prefilled with CHF", async () => {
    render(wrap(<ImportPage />));
    await showConfigPanel();
    await waitFor(() => {
      expect(screen.getByLabelText(/default currency/i).textContent).toMatch(/CHF/);
    });
  });

  it("renders a Currency column-mapping input", async () => {
    render(wrap(<ImportPage />));
    await showConfigPanel();
    await waitFor(() => {
      expect(screen.getByLabelText(/currency col/i)).toBeInTheDocument();
    });
  });
});

describe("ImportPage — commit invalidates query caches", () => {
  it("invalidates transactions, budgets, and forecast after a successful commit", async () => {
    // Seed an "Imported" category so ensureImportedCategory() doesn't need to
    // create one (keeps the invalidation call count tight to the mutation).
    testState.categories = [
      {
        id: 1,
        name: "Imported",
        kind: "expense",
        target_amount: null,
        target_date: null,
        created_at: new Date().toISOString(),
      },
    ];
    testState.nextCatId = 2;

    const { tree, spy } = wrapWithSpy(<ImportPage />);
    render(tree);

    // 1. Upload a CSV file.
    const csvContent = "2026-05-01;Coffee;-4.50";
    const file = new File([csvContent], "test.csv", { type: "text/csv" });
    Object.defineProperty(file, "text", {
      value: () => Promise.resolve(csvContent),
      writable: false,
    });
    const fileInput = document.querySelector(
      "input[type='file']",
    ) as HTMLInputElement;
    await userEvent.upload(fileInput, file);

    // 2. Preview the file to populate the review table.
    const previewBtn = await screen.findByRole("button", { name: /preview/i });
    await userEvent.click(previewBtn);

    // 3. The Import button shows the selection count when the table renders.
    //    Our preview handler returns 1 eligible non-duplicate row → "Import 1".
    const importBtn = await screen.findByRole("button", { name: /^import 1$/i });
    spy.mockClear(); // ignore any incidental invalidations during render
    await userEvent.click(importBtn);

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["transactions"] }),
      );
    });
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["budgets"] }),
    );
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["forecast"] }),
    );
    expect(spy).toHaveBeenCalledTimes(3);
  });
});
