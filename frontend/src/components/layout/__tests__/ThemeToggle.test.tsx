import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeToggle } from "../ThemeToggle";

describe("ThemeToggle (3-segment)", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark", "sakura", "cyberpunk");
    window.localStorage.clear();
  });

  it("renders three buttons with aria-labels", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: /sakura theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /light theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dark theme/i })).toBeInTheDocument();
  });

  it("clicking sakura applies the .sakura class", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: /sakura theme/i }));
    expect(document.documentElement.classList.contains("sakura")).toBe(true);
  });

  it("clicking dark applies .dark and removes .sakura", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: /sakura theme/i }));
    fireEvent.click(screen.getByRole("button", { name: /dark theme/i }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("sakura")).toBe(false);
  });

  it("has a 4th button for cyberpunk", () => {
    render(<ThemeToggle />);
    expect(screen.getByLabelText(/cyberpunk theme/i)).toBeInTheDocument();
  });
});
