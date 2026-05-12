import { describe, it, expect } from "vitest";
import { createCategory } from "@/api/categories";
import {
  createTransaction,
  listTransactions,
  deleteTransaction,
} from "@/api/transactions";

describe("transactions api", () => {
  it("creates, filters by month, deletes", async () => {
    const cat = await createCategory({ name: "Groceries" });
    await createTransaction({
      amount: "12.34",
      date: "2026-05-10",
      category_id: cat.id,
      description: "Milk",
    });
    await createTransaction({
      amount: "5.00",
      date: "2026-04-20",
      category_id: cat.id,
      description: "old",
    });

    const may = await listTransactions({ month: "2026-05" });
    expect(may).toHaveLength(1);
    expect(may[0].description).toBe("Milk");

    await deleteTransaction(may[0].id);
    expect(await listTransactions({ month: "2026-05" })).toEqual([]);
  });
});
