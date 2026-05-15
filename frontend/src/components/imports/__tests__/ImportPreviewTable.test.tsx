import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ImportPreviewTable } from "../ImportPreviewTable";
import type { ParsedRow, Category } from "@/api/types";

const cats: Category[] = [
  {
    id: 1,
    name: "Imported",
    kind: "expense",
    target_amount: null,
    target_date: null,
    created_at: "",
  },
  {
    id: 2,
    name: "Groceries",
    kind: "expense",
    target_amount: null,
    target_date: null,
    created_at: "",
  },
];

const rows: ParsedRow[] = [
  {
    row_index: 0,
    date: "2026-05-13",
    description: "COOP",
    amount: "-45.30",
    currency: null,
    kind_hint: "expense",
    is_duplicate: false,
    errors: [],
  },
  {
    row_index: 1,
    date: "2026-05-13",
    description: "Spotify",
    amount: "-15.95",
    currency: null,
    kind_hint: "expense",
    is_duplicate: true,
    errors: [],
  },
];

describe("ImportPreviewTable", () => {
  it("renders rows; non-dupes ticked by default, dupes unticked", () => {
    render(
      <ImportPreviewTable
        rows={rows}
        categories={cats}
        defaultCategoryId={1}
        onSelectionsChange={() => {}}
      />,
    );
    expect(screen.getByText("COOP")).toBeInTheDocument();
    expect(screen.getByText("Spotify")).toBeInTheDocument();
    expect(screen.getByText(/Duplicate/i)).toBeInTheDocument();

    const cooprow = screen.getByText("COOP").closest("tr") as HTMLElement;
    const spotifyRow = screen.getByText("Spotify").closest("tr") as HTMLElement;
    const coopCheckbox = cooprow.querySelector(
      '[role="checkbox"]',
    ) as HTMLElement;
    const spotifyCheckbox = spotifyRow.querySelector(
      '[role="checkbox"]',
    ) as HTMLElement;

    expect(coopCheckbox.getAttribute("aria-checked")).toBe("true");
    expect(spotifyCheckbox.getAttribute("aria-checked")).toBe("false");
  });

  it("emits selections including dupes when user ticks them", () => {
    const onSelectionsChange = vi.fn();
    render(
      <ImportPreviewTable
        rows={rows}
        categories={cats}
        defaultCategoryId={1}
        onSelectionsChange={onSelectionsChange}
      />,
    );
    const spotifyRow = screen.getByText("Spotify").closest("tr") as HTMLElement;
    const spotifyCheckbox = spotifyRow.querySelector(
      '[role="checkbox"]',
    ) as HTMLElement;
    fireEvent.click(spotifyCheckbox);

    const calls = onSelectionsChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    const indexes = lastCall.map((s: { row_index: number }) => s.row_index).sort();
    expect(indexes).toEqual([0, 1]);
  });
});
