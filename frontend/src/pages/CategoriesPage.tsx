import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CategoriesList } from "@/components/categories/CategoriesList";
import { CategoryFormDialog } from "@/components/categories/CategoryFormDialog";

export default function CategoriesPage() {
  const [open, setOpen] = useState(false);
  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Categories</h2>
        <Button onClick={() => setOpen(true)} size="sm">
          <Plus className="h-4 w-4 mr-1" /> New category
        </Button>
      </div>
      <CategoriesList />
      <CategoryFormDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}
