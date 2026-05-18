import { useRef, type KeyboardEvent } from "react";
import { useTheme, type Theme } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";

interface Swatch {
  key: Theme;
  label: string;
  preview: {
    background: string;
    foreground: string;
    primary: string;
    accent: string;
  };
}

const SWATCHES: Swatch[] = [
  {
    key: "light",
    label: "Light",
    preview: {
      background: "hsl(0 0% 100%)",
      foreground: "hsl(240 10% 4%)",
      primary: "hsl(240 6% 10%)",
      accent: "hsl(240 5% 90%)",
    },
  },
  {
    key: "dark",
    label: "Dark",
    preview: {
      background: "hsl(240 10% 4%)",
      foreground: "hsl(0 0% 98%)",
      primary: "hsl(0 0% 98%)",
      accent: "hsl(240 4% 16%)",
    },
  },
  {
    key: "sakura",
    label: "Sakura",
    preview: {
      background: "hsl(290 30% 8%)",
      foreground: "hsl(0 0% 96%)",
      primary: "hsl(340 65% 68%)",
      accent: "hsl(280 50% 65%)",
    },
  },
  {
    key: "cyberpunk",
    label: "Cyberpunk",
    preview: {
      background: "hsl(240 15% 6%)",
      foreground: "hsl(60 100% 96%)",
      primary: "hsl(56 100% 51%)",
      accent: "hsl(187 100% 50%)",
    },
  },
  {
    key: "emerald",
    label: "Emerald",
    preview: {
      background: "hsl(155 25% 7%)",
      foreground: "hsl(150 15% 92%)",
      primary: "hsl(152 55% 48%)",
      accent: "hsl(175 50% 35%)",
    },
  },
  {
    key: "navy",
    label: "Navy",
    preview: {
      background: "hsl(220 30% 98%)",
      foreground: "hsl(220 60% 15%)",
      primary: "hsl(220 75% 28%)",
      accent: "hsl(195 55% 88%)",
    },
  },
];

export function AppearanceSection() {
  const { theme, setTheme } = useTheme();
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);

  function focusAndSelect(nextIndex: number) {
    const wrapped = (nextIndex + SWATCHES.length) % SWATCHES.length;
    const next = SWATCHES[wrapped];
    setTheme(next.key);
    buttonRefs.current[wrapped]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    switch (event.key) {
      case "ArrowRight":
      case "ArrowDown":
        event.preventDefault();
        focusAndSelect(index + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
        event.preventDefault();
        focusAndSelect(index - 1);
        break;
      case "Home":
        event.preventDefault();
        focusAndSelect(0);
        break;
      case "End":
        event.preventDefault();
        focusAndSelect(SWATCHES.length - 1);
        break;
    }
  }

  return (
    <div role="radiogroup" aria-label="Theme" className="grid grid-cols-2 gap-3">
      {SWATCHES.map((s, index) => {
        const checked = theme === s.key;
        return (
          <button
            key={s.key}
            ref={(el) => { buttonRefs.current[index] = el; }}
            type="button"
            role="radio"
            aria-checked={checked}
            aria-label={s.label}
            tabIndex={checked ? 0 : -1}
            onClick={() => setTheme(s.key)}
            onKeyDown={(e) => onKeyDown(e, index)}
            className={cn(
              "flex flex-col gap-2 rounded-md border-2 p-3 text-left",
              checked ? "border-primary" : "border-transparent",
            )}
          >
            <div
              className="h-16 w-full rounded-sm flex items-center justify-between px-3 text-xs font-mono"
              style={{
                backgroundColor: s.preview.background,
                color: s.preview.foreground,
                borderRadius: s.key === "cyberpunk" ? 0 : undefined,
              }}
            >
              <span
                className="inline-block h-3 w-3 rounded-sm"
                style={{
                  backgroundColor: s.preview.primary,
                  borderRadius: s.key === "cyberpunk" ? 0 : undefined,
                }}
              />
              <span
                className="inline-block h-3 w-3 rounded-sm"
                style={{
                  backgroundColor: s.preview.accent,
                  borderRadius: s.key === "cyberpunk" ? 0 : undefined,
                }}
              />
              <span>Aa</span>
            </div>
            <span className="text-sm font-medium">{s.label}</span>
          </button>
        );
      })}
    </div>
  );
}
