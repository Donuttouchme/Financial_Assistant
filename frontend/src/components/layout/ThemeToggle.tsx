import { Moon, Sun, Flower2 } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";

type ThemeName = "sakura" | "light" | "dark";
const OPTIONS: Array<{
  key: ThemeName;
  label: string;
  Icon: React.ComponentType<{ className?: string }>;
}> = [
  { key: "sakura", label: "Sakura theme", Icon: Flower2 },
  { key: "light",  label: "Light theme",  Icon: Sun },
  { key: "dark",   label: "Dark theme",   Icon: Moon },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="inline-flex items-center rounded-md border bg-card p-0.5">
      {OPTIONS.map(({ key, label, Icon }) => (
        <button
          key={key}
          type="button"
          aria-label={label}
          aria-pressed={theme === key}
          onClick={() => setTheme(key)}
          className={cn(
            "inline-flex items-center justify-center h-7 w-7 rounded",
            theme === key
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
        >
          <Icon className="h-4 w-4" />
        </button>
      ))}
    </div>
  );
}
