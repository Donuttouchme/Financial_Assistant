import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { Header } from "../Header";

function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="loc">{loc.pathname + loc.search}</div>;
}

function renderHeader(initial: string) {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Header onAddTransaction={() => {}} />
      <LocationProbe />
    </MemoryRouter>,
  );
}

afterEach(() => vi.useRealTimers());

describe("Header search", () => {
  it("navigates to /transactions?q= after debounce once term >= 2 chars", () => {
    vi.useFakeTimers();
    renderHeader("/dashboard");
    const input = screen.getByLabelText("Search transactions");

    fireEvent.change(input, { target: { value: "etterem" } });
    act(() => vi.advanceTimersByTime(300));

    expect(screen.getByTestId("loc").textContent).toBe("/transactions?q=etterem");
  });

  it("disables the month picker while a search is active", () => {
    renderHeader("/transactions?q=etterem");
    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("preserves an existing ?month= when starting a search", () => {
    vi.useFakeTimers();
    renderHeader("/transactions?month=2026-01");
    const input = screen.getByLabelText("Search transactions");

    fireEvent.change(input, { target: { value: "etterem" } });
    act(() => vi.advanceTimersByTime(300));

    expect(screen.getByTestId("loc").textContent).toBe(
      "/transactions?month=2026-01&q=etterem",
    );
  });

  it("clearing the box drops ?q= and keeps the month", () => {
    vi.useFakeTimers();
    renderHeader("/transactions?month=2026-01&q=etterem");
    const input = screen.getByLabelText("Search transactions");

    fireEvent.change(input, { target: { value: "" } });
    act(() => vi.advanceTimersByTime(300));

    expect(screen.getByTestId("loc").textContent).toBe(
      "/transactions?month=2026-01",
    );
  });
});
