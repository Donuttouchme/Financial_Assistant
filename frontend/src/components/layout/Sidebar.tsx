import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Receipt, Tag, TrendingUp, Wallet, Download, Upload, Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

function Logo() {
  return (
    <svg
      role="img"
      aria-label="Financial Assistant"
      viewBox="0 0 32 32"
      className="h-6 w-6 text-primary"
    >
      <circle cx="16" cy="16" r="12" fill="none" stroke="currentColor" strokeWidth="3" />
      <path
        d="M 16 16 L 16 4 A 12 12 0 0 1 28 16 Z"
        fill="currentColor"
      />
    </svg>
  );
}

const links = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/forecast", label: "Forecast", icon: TrendingUp },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/categories", label: "Categories", icon: Tag },
  { to: "/budgets", label: "Budgets", icon: Wallet },
  { to: "/import", label: "Import", icon: Upload },
  { to: "/export", label: "Export", icon: Download },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r bg-card flex flex-col">
      <div className="px-4 py-5 flex items-center gap-2 font-semibold text-lg">
        <Logo />
        <span>Financial Assistant</span>
      </div>
      <nav className="flex-1 px-2 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
