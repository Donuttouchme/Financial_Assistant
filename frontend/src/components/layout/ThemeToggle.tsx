import {
  Moon, Sun, Flower2, Zap, Leaf, Anchor, ChevronDown, Check,
} from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme, type Theme } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";

const OPTIONS: Array<{
  key: Theme;
  label: string;
  Icon: React.ComponentType<{ className?: string }>;
}> = [
  { key: "light",     label: "Light",     Icon: Sun },
  { key: "dark",      label: "Dark",      Icon: Moon },
  { key: "sakura",    label: "Sakura",    Icon: Flower2 },
  { key: "cyberpunk", label: "Cyberpunk", Icon: Zap },
  { key: "emerald",   label: "Emerald",   Icon: Leaf },
  { key: "navy",      label: "Navy",      Icon: Anchor },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const current = OPTIONS.find((o) => o.key === theme) ?? OPTIONS[0];
  const CurrentIcon = current.Icon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Theme"
        className="inline-flex items-center gap-1 h-8 px-2 rounded-md border bg-card text-foreground hover:bg-accent hover:text-accent-foreground"
      >
        <CurrentIcon className="h-4 w-4" />
        <ChevronDown className="h-3 w-3 opacity-70" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[10rem]">
        {OPTIONS.map(({ key, label, Icon }) => (
          <DropdownMenuItem
            key={key}
            onSelect={() => setTheme(key)}
            aria-label={`${label} theme`}
            className={cn(
              "flex items-center gap-2 cursor-pointer",
              key === theme && "bg-accent text-accent-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
            <span className="flex-1">{label}</span>
            {key === theme && <Check className="h-3.5 w-3.5" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
