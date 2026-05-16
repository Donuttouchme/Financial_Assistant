import * as React from "react";
import { format, parse } from "date-fns";
import { Calendar as CalendarIcon } from "lucide-react";

import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

const ISO = "yyyy-MM-dd";
const DISPLAY = "yyyy-MM-dd";

function parseIso(value: string): Date | undefined {
  if (!value) return undefined;
  const d = parse(value, ISO, new Date());
  return isNaN(d.getTime()) ? undefined : d;
}

interface Props {
  /** ISO date string YYYY-MM-DD (backend / form value). */
  value: string;
  onChange: (value: string) => void;
  id?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
}

/**
 * Theme-aware replacement for <input type="date">. The native control's
 * OS-rendered calendar popup does not honor our CSS variables; this Radix
 * Popover + react-day-picker combo does.
 */
export const DatePicker = React.forwardRef<HTMLButtonElement, Props>(
  function DatePicker({ value, onChange, id, disabled, className, ...rest }, ref) {
    const [open, setOpen] = React.useState(false);
    const selected = parseIso(value);
    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            ref={ref}
            id={id}
            type="button"
            disabled={disabled}
            aria-label={rest["aria-label"] ?? "Pick a date"}
            className={cn(
              "flex h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
              !selected && "text-muted-foreground",
              className,
            )}
          >
            <span>{selected ? format(selected, DISPLAY) : "Pick a date"}</span>
            <CalendarIcon className="ml-2 h-4 w-4 opacity-70" aria-hidden="true" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={selected}
            onSelect={(d) => {
              if (d) {
                onChange(format(d, ISO));
                setOpen(false);
              }
            }}
            initialFocus
          />
        </PopoverContent>
      </Popover>
    );
  },
);
