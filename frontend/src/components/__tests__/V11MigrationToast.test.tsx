import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import { V11MigrationToast } from "@/components/V11MigrationToast";

vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
    success: vi.fn(),
  },
  Toaster: () => null,
}));

beforeEach(() => {
  window.localStorage.clear();
  vi.clearAllMocks();
});

describe("V11MigrationToast", () => {
  it("fires the toast on first mount", async () => {
    render(<V11MigrationToast />);
    await waitFor(() => {
      expect(toast.info).toHaveBeenCalledWith(
        expect.stringContaining("Multi-currency"),
        expect.objectContaining({ duration: expect.any(Number) }),
      );
    });
  });

  it("does not fire when the flag is already set", async () => {
    window.localStorage.setItem("fa-v11-notice-dismissed", "1");
    render(<V11MigrationToast />);
    await new Promise((r) => setTimeout(r, 50));
    expect(toast.info).not.toHaveBeenCalled();
  });

  it("sets the flag immediately so it never re-fires within the same install", async () => {
    render(<V11MigrationToast />);
    await waitFor(() => {
      expect(window.localStorage.getItem("fa-v11-notice-dismissed")).toBe("1");
    });
  });
});
