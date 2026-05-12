import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import {
  TransactionFormDialog,
} from "@/components/transactions/TransactionFormDialog";

export function AppShell() {
  const [addOpen, setAddOpen] = useState(false);
  return (
    <div className="flex h-screen w-screen bg-background text-foreground">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header onAddTransaction={() => setAddOpen(true)} />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <TransactionFormDialog
        mode="create"
        open={addOpen}
        onOpenChange={setAddOpen}
      />
    </div>
  );
}
