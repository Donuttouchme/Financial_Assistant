import { useEffect, useState } from "react";

type Theme = "light" | "dark" | "sakura" | "cyberpunk" | "emerald" | "navy";
const STORAGE_KEY = "fa-theme";
const VALID: Theme[] = ["light", "dark", "sakura", "cyberpunk", "emerald", "navy"];

// Per-theme favicon. Browsers don't apply page CSS to linked favicons, so we
// emit one SVG per theme with the accent color baked in and swap the <link>
// href when the theme changes. The shape matches frontend/public/favicon.svg.
const FAVICON_COLORS: Record<Theme, string> = {
  light:     "#0f0f12",
  dark:      "#fafafa",
  sakura:    "#e35d8a",
  cyberpunk: "#fcee0a",
  emerald:   "#3eba83",
  navy:      "#143d7a",
};

function faviconSvg(color: string): string {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">` +
    `<circle cx="16" cy="16" r="12" fill="none" stroke="${color}" stroke-width="3"/>` +
    `<path d="M 16 4 A 12 12 0 0 1 28 16 L 22 16 A 6 6 0 0 0 16 10 Z" fill="${color}"/>` +
    `</svg>`
  );
}

function applyFavicon(theme: Theme): void {
  const svg = faviconSvg(FAVICON_COLORS[theme]);
  const href = `data:image/svg+xml,${encodeURIComponent(svg)}`;
  let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (!link) {
    link = document.createElement("link");
    link.rel = "icon";
    document.head.appendChild(link);
  }
  link.type = "image/svg+xml";
  link.href = href;
}

function readInitialTheme(): Theme {
  // First-run default is always light. The user's choice is persisted in
  // localStorage and takes precedence on subsequent loads. We deliberately
  // do NOT honor prefers-color-scheme here — it conflicts with users who
  // run their OS in dark mode but still want this app to start light.
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored && (VALID as string[]).includes(stored)) return stored as Theme;
  return "light";
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "sakura", "cyberpunk", "emerald", "navy");
    if (theme !== "light") root.classList.add(theme);
    window.localStorage.setItem(STORAGE_KEY, theme);
    applyFavicon(theme);
  }, [theme]);

  return { theme, setTheme };
}

export type { Theme };
