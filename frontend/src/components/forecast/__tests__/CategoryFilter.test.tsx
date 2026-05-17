import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { CategoryFilter } from "../CategoryFilter";

function ShowUrl() {
  const loc = useLocation();
  return <span data-testid="url">{loc.search}</span>;
}

const sampleCategories = [
  { id: 1, name: "Food", kind: "expense" as const, target_amount: null, target_date: null, created_at: "2024-01-01" },
  { id: 2, name: "Rent", kind: "expense" as const, target_amount: null, target_date: null, created_at: "2024-01-01" },
];

describe("CategoryFilter", () => {
  it("renders All by default when ?category= is absent", () => {
    render(
      <MemoryRouter initialEntries={["/forecast"]}>
        <CategoryFilter categories={sampleCategories} />
      </MemoryRouter>,
    );
    const select = screen.getByLabelText(/category/i) as HTMLSelectElement;
    expect(select.value).toBe("all");
  });

  it("writes ?category=<id> when a category is picked", () => {
    render(
      <MemoryRouter initialEntries={["/forecast"]}>
        <CategoryFilter categories={sampleCategories} />
        <ShowUrl />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: "1" } });
    expect(screen.getByTestId("url").textContent).toContain("category=1");
  });

  it("removes the param when switching back to All", () => {
    render(
      <MemoryRouter initialEntries={["/forecast?category=2"]}>
        <CategoryFilter categories={sampleCategories} />
        <ShowUrl />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: "all" } });
    expect(screen.getByTestId("url").textContent).not.toContain("category=");
  });
});
