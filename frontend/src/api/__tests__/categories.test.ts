import { describe, it, expect } from "vitest";
import {
  createCategory,
  listCategories,
  deleteCategory,
} from "@/api/categories";
import { HttpError } from "@/api/client";

describe("categories api", () => {
  it("creates and lists categories", async () => {
    await createCategory({ name: "Groceries" });
    await createCategory({ name: "Salary", kind: "income" });
    const cats = await listCategories();
    expect(cats.map((c) => `${c.name}:${c.kind}`).sort()).toEqual([
      "Groceries:expense",
      "Salary:income",
    ]);
  });

  it("translates 400 to HttpError with detail", async () => {
    await createCategory({ name: "Dup" });
    await expect(createCategory({ name: "Dup" })).rejects.toMatchObject({
      status: 400,
      detail: expect.stringContaining("already exists"),
    });
  });

  it("deletes a category", async () => {
    const cat = await createCategory({ name: "Misc" });
    await deleteCategory(cat.id);
    expect(await listCategories()).toEqual([]);
  });

  it("HttpError 404 from delete-unknown", async () => {
    await expect(deleteCategory(9999)).rejects.toBeInstanceOf(HttpError);
  });
});
