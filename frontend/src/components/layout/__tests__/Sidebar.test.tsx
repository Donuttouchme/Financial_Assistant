import { it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";

it("sidebar has a Settings link", () => {
  render(<MemoryRouter><Sidebar /></MemoryRouter>);
  expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute("href", "/settings");
});

it("renders the logo icon", () => {
  render(<MemoryRouter><Sidebar /></MemoryRouter>);
  expect(screen.getByRole("img", { name: /financial assistant/i })).toBeInTheDocument();
});
