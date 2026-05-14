import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SavingsGoalCard } from "../SavingsGoalCard";

describe("SavingsGoalCard", () => {
  it("shows saved / target, percent, and days-left", () => {
    render(
      <SavingsGoalCard
        name="Vacation 2027"
        saved={2400}
        target={3000}
        targetDate="2027-06-30"
        today={new Date("2026-11-27")}
      />,
    );
    expect(screen.getByText("Vacation 2027")).toBeInTheDocument();
    expect(screen.getByText(/80%/)).toBeInTheDocument();
    // days from 2026-11-27 to 2027-06-30 is 215
    expect(screen.getByText(/215 days left/)).toBeInTheDocument();
  });

  it("omits days-left when targetDate is null", () => {
    render(
      <SavingsGoalCard
        name="Pillar 3a"
        saved={6300}
        target={7056}
        targetDate={null}
        today={new Date("2026-05-13")}
      />,
    );
    expect(screen.queryByText(/days left/i)).toBeNull();
    expect(screen.getByText(/no deadline/i)).toBeInTheDocument();
  });

  it("renders a goal without target gracefully", () => {
    render(
      <SavingsGoalCard
        name="Emergency"
        saved={1200}
        target={null}
        targetDate={null}
        today={new Date("2026-05-13")}
      />,
    );
    expect(screen.getByText("Emergency")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });
});
