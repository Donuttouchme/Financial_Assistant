import { useEffect } from "react";
import { toast } from "sonner";

const STORAGE_KEY = "fa-v1.2-toast-shown";

export function V12MigrationToast() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(STORAGE_KEY) === "1") return;

    // Defer slightly so the toast pops after the UI hydrates.
    const id = window.setTimeout(() => {
      toast("What's new in v1.2", {
        description:
          "Forecast graph on your dashboard + two new themes (emerald, navy). Settings → Appearance.",
        duration: 10000,
      });
      window.localStorage.setItem(STORAGE_KEY, "1");
    }, 1200);

    return () => window.clearTimeout(id);
  }, []);

  return null;
}
