import { useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import { useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { useActiveSearch } from "@/hooks/useActiveSearch";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { monthOptions } from "@/lib/date";
import { ThemeToggle } from "./ThemeToggle";

interface HeaderProps {
  onAddTransaction: () => void;
}

export function Header({ onAddTransaction }: HeaderProps) {
  const { month, setMonth } = useUrlMonth();
  const opts = monthOptions();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const activeSearch = useActiveSearch();

  const urlQ = params.get("q") ?? "";
  const [text, setText] = useState(urlQ);
  const debounced = useDebouncedValue(text, 300);

  // Keep the box in sync when ?q= changes from outside (back button, clearing).
  useEffect(() => {
    setText(urlQ);
  }, [urlQ]);

  // Push the debounced term into the URL. >= 2 chars -> /transactions?q=term;
  // otherwise drop an existing ?q=. No-op on non-transactions pages with no q.
  useEffect(() => {
    const term = debounced.trim();
    const next = new URLSearchParams(params);
    if (term.length >= 2) {
      next.set("q", term);
      const target = `/transactions?${next.toString()}`;
      if (location.pathname + location.search !== target) {
        navigate(target);
      }
    } else if (params.get("q")) {
      next.delete("q");
      const qs = next.toString();
      navigate(`/transactions${qs ? `?${qs}` : ""}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  return (
    <header className="h-14 border-b bg-card flex items-center justify-between px-4">
      <div className="flex items-center gap-2">
        <Select
          value={month}
          onValueChange={setMonth}
          disabled={activeSearch !== null}
        >
          <SelectTrigger
            className="w-40"
            title={
              activeSearch !== null
                ? "Clear search to pick a month"
                : undefined
            }
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {opts.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="relative w-64">
          <Search className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            aria-label="Search transactions"
            placeholder="Search transactions…"
            className="pl-8"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setText("");
            }}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button onClick={onAddTransaction} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          Add transaction
        </Button>
      </div>
    </header>
  );
}
