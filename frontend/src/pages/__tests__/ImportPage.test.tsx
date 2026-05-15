import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import ImportPage from "@/pages/ImportPage";
import { resetTestState } from "@/tests/handlers";

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
      expect(screen.getByLabelText(/default currency/i)).toHaveValue("CHF");
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
