import { describe, expect, it, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppearanceSection } from "@/components/settings/AppearanceSection";

describe("AppearanceSection", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark", "sakura", "cyberpunk");
    window.localStorage.clear();
  });

  it("has 4 theme cards", () => {
    render(<AppearanceSection />);
    expect(screen.getByRole("radio", { name: /light/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /dark/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /sakura/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /cyberpunk/i })).toBeInTheDocument();
  });

  it("clicking a card applies that theme", async () => {
    const user = userEvent.setup();
    render(<AppearanceSection />);
    await user.click(screen.getByRole("radio", { name: /cyberpunk/i }));
    expect(document.documentElement.classList.contains("cyberpunk")).toBe(true);
  });

  it("ArrowRight on the focused card moves selection to the next theme", async () => {
    const user = userEvent.setup();
    render(<AppearanceSection />);
    const light = screen.getByRole("radio", { name: /light/i });
    light.focus();
    await user.keyboard("{ArrowRight}");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("only the checked card is in the tab order", () => {
    render(<AppearanceSection />);
    const light = screen.getByRole("radio", { name: /light/i });
    const dark = screen.getByRole("radio", { name: /dark/i });
    expect(light.getAttribute("tabindex")).toBe("0");
    expect(dark.getAttribute("tabindex")).toBe("-1");
  });
});
