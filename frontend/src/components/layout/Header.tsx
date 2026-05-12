import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { monthOptions } from "@/lib/date";
import { ThemeToggle } from "./ThemeToggle";

interface HeaderProps {
  onAddTransaction: () => void;
}

export function Header({ onAddTransaction }: HeaderProps) {
  const { month, setMonth } = useUrlMonth();
  const opts = monthOptions();

  return (
    <header className="h-14 border-b bg-card flex items-center justify-between px-4">
      <Select value={month} onValueChange={setMonth}>
        <SelectTrigger className="w-40">
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
