import { format, parse, subMonths } from "date-fns";

export function currentMonth(now: Date = new Date()): string {
  return format(now, "yyyy-MM");
}

export function monthLabel(month: string): string {
  return format(parse(month, "yyyy-MM", new Date()), "MMMM yyyy");
}

export interface MonthOption {
  value: string;
  label: string;
}

export function monthOptions(endMonth: string = currentMonth()): MonthOption[] {
  const end = parse(endMonth, "yyyy-MM", new Date());
  const opts: MonthOption[] = [];
  for (let i = 0; i < 24; i++) {
    const d = subMonths(end, i);
    opts.push({ value: format(d, "yyyy-MM"), label: format(d, "MMMM yyyy") });
  }
  return opts;
}
