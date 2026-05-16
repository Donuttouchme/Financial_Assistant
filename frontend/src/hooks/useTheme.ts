import { useEffect, useState } from "react";

type Theme = "light" | "dark" | "sakura" | "cyberpunk";
const STORAGE_KEY = "fa-theme";
const VALID: Theme[] = ["light", "dark", "sakura", "cyberpunk"];

function readInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored && (VALID as string[]).includes(stored)) return stored as Theme;
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "sakura", "cyberpunk");
    if (theme !== "light") root.classList.add(theme);
    window.localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  return { theme, setTheme };
}

export type { Theme };
