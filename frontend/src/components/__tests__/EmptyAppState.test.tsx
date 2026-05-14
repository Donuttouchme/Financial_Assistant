import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { EmptyAppState } from "../EmptyAppState";

function renderWithRouter(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("EmptyAppState", () => {
  it("shows the welcome message and a CTA link to /categories", () => {
    renderWithRouter(<EmptyAppState />);
    expect(screen.getByText(/welcome to financial assistant/i)).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: /create your first category/i });
    expect(cta).toHaveAttribute("href", "/categories");
  });
});
