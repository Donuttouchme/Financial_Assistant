import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "@/components/ErrorBoundary";

function Boom(): JSX.Element {
  throw new Error("kaboom");
}

describe("ErrorBoundary", () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <p>hello</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("catches render errors and shows a reload affordance", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("button", { name: /reload/i })).toBeInTheDocument();
  });
});
