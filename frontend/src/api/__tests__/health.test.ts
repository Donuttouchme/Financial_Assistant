import { describe, it, expect } from "vitest";
import { getHealth } from "@/api/health";

describe("health api", () => {
  it("returns ok", async () => {
    expect(await getHealth()).toEqual({ status: "ok" });
  });
});
