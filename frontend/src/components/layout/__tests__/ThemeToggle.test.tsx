import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeToggle } from "../ThemeToggle";

describe("ThemeToggle (3-segment)", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark", "sakura", "cyberpunk", "emerald", "navy");
    window.localStorage.clear();
  });

  it("renders buttons with aria-labels for all themes", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: "Sakura theme" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Light theme" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dark theme" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Emerald-dark theme" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Navy-light theme" })).toBeInTheDocument();
  });

  it("clicking sakura applies the .sakura class", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: "Sakura theme" }));
    expect(document.documentElement.classList.contains("sakura")).toBe(true);
  });

  it("clicking dark applies .dark and removes .sakura", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: "Sakura theme" }));
    fireEvent.click(screen.getByRole("button", { name: "Dark theme" }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("sakura")).toBe(false);
  });

  it("has a button for cyberpunk", () => {
    render(<ThemeToggle />);
    expect(screen.getByLabelText("Cyberpunk theme")).toBeInTheDocument();
  });
});
