import { useSearchParams } from "react-router-dom";

/**
 * Single source of truth for "is a search active": reads ?q=, trims it, and
 * returns the term only once it has >= 2 characters, else null. Shared by the
 * global Header (to disable the month picker) and the Transactions page.
 */
export function useActiveSearch(): string | null {
  const [params] = useSearchParams();
  const term = (params.get("q") ?? "").trim();
  return term.length >= 2 ? term : null;
}
