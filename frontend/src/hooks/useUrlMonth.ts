import { useSearchParams } from "react-router-dom";
import { currentMonth } from "@/lib/date";

export interface UrlMonth {
  month: string;
  setMonth: (next: string) => void;
}

export function useUrlMonth(): UrlMonth {
  const [params, setParams] = useSearchParams();
  const raw = params.get("month");
  const month = raw && /^\d{4}-(0[1-9]|1[0-2])$/.test(raw) ? raw : currentMonth();

  function setMonth(next: string) {
    const newParams = new URLSearchParams(params);
    newParams.set("month", next);
    setParams(newParams, { replace: false });
  }

  return { month, setMonth };
}
