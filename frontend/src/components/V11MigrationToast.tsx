import { useEffect } from "react";
import { toast } from "sonner";

const STORAGE_KEY = "fa-v11-notice-dismissed";

export function V11MigrationToast() {
  useEffect(() => {
    if (window.localStorage.getItem(STORAGE_KEY) === "1") return;
    window.localStorage.setItem(STORAGE_KEY, "1");
    toast.info(
      "Multi-currency support is now available. Set your default currency in Settings if needed.",
      { duration: 8000 },
    );
  }, []);

  return null;
}
