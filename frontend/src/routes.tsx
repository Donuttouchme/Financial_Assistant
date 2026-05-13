import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import DashboardPage from "@/pages/DashboardPage";
import TransactionsPage from "@/pages/TransactionsPage";
import CategoriesPage from "@/pages/CategoriesPage";
import BudgetsPage from "@/pages/BudgetsPage";
import ExportPage from "@/pages/ExportPage";
import ImportPage from "@/pages/ImportPage";
import NotFoundPage from "@/pages/NotFoundPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "transactions", element: <TransactionsPage /> },
      { path: "categories", element: <CategoriesPage /> },
      { path: "budgets", element: <BudgetsPage /> },
      { path: "import", element: <ImportPage /> },
      { path: "export", element: <ExportPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
