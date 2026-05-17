import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "../ThemeToggle";

describe("ThemeToggle dropdown", () => {
  beforeEach(() => {
    document.documentElement.classList.remove(
      "dark", "sakura", "cyberpunk", "emerald", "navy",
    );
    window.localStorage.clear();
  });

  it("renders a single trigger button with Theme aria-label", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: "Theme" })).toBeInTheDocument();
  });

  it("does not render menu items until the trigger is clicked", () => {
    render(<ThemeToggle />);
    expect(screen.queryByRole("menuitem", { name: /sakura theme/i })).toBeNull();
  });

  it("opens a menu with all six theme options when triggered", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(screen.getByRole("button", { name: "Theme" }));
    expect(await screen.findByRole("menuitem", { name: /light theme/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /dark theme/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /sakura theme/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /cyberpunk theme/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /emerald theme/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /navy theme/i })).toBeInTheDocument();
  });

  it("selecting sakura applies the .sakura class", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(screen.getByRole("button", { name: "Theme" }));
    await user.click(await screen.findByRole("menuitem", { name: /sakura theme/i }));
    expect(document.documentElement.classList.contains("sakura")).toBe(true);
  });

  it("selecting dark after sakura removes .sakura and adds .dark", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(screen.getByRole("button", { name: "Theme" }));
    await user.click(await screen.findByRole("menuitem", { name: /sakura theme/i }));
    await user.click(screen.getByRole("button", { name: "Theme" }));
    await user.click(await screen.findByRole("menuitem", { name: /dark theme/i }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("sakura")).toBe(false);
  });
});
