import { useMemo } from "react";
import {
  Area, AreaChart, CartesianGrid, ReferenceLine,
  XAxis, YAxis,
} from "recharts";
import { format, parseISO } from "date-fns";

import {
  ChartContainer, ChartTooltip, ChartTooltipContent,
} from "@/components/ui/chart";
import { formatMoney } from "@/lib/money";
import type {
  DailyCumulativeResponse, MonthlyBucketsResponse,
} from "@/api/types";

type Props =
  | { mode: "daily"; daily: DailyCumulativeResponse }
  | { mode: "monthly"; monthly: MonthlyBucketsResponse };

export function ForecastChart(props: Props) {
  if (props.mode === "daily") return <DailyChart data={props.daily} />;
  return <MonthlyChart data={props.monthly} />;
}

function DailyChart({ data }: { data: DailyCumulativeResponse }) {
  const baseCcy = data.base_currency;
  const today = data.today;

  // Two parallel series so we can style past (solid) and forecast (translucent
  // + dashed) independently. The "today" point appears in both series so the
  // line connects cleanly across the transition.
  const series = useMemo(
    () => data.points.map((p) => ({
      date: p.date,
      day: format(parseISO(p.date), "d"),
      actual: !p.is_forecast || p.date === today ? Number(p.cumulative) : null,
      forecast: p.is_forecast || p.date === today ? Number(p.cumulative) : null,
    })),
    [data.points, today],
  );

  const config = {
    actual: { label: "Actual", color: "hsl(var(--chart-1))" },
    forecast: { label: "Forecast", color: "hsl(var(--chart-1))" },
  };

  return (
    <ChartContainer config={config} className="h-72 w-full">
      <AreaChart data={series}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey="day" tickLine={false} axisLine={false} />
        <YAxis tickLine={false} axisLine={false} width={50} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              formatter={(value) =>
                value === null ? "" : formatMoney(Number(value), baseCcy)
              }
            />
          }
        />
        <ReferenceLine
          x={format(parseISO(today), "d")}
          stroke="hsl(var(--muted-foreground))"
          strokeDasharray="2 2"
          label={{ value: "Today", position: "top", fontSize: 11 }}
        />
        <Area
          type="monotone"
          dataKey="actual"
          stroke="var(--color-actual)"
          strokeWidth={2.5}
          fill="var(--color-actual)"
          fillOpacity={0.18}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Area
          type="monotone"
          dataKey="forecast"
          stroke="var(--color-forecast)"
          strokeWidth={1.5}
          strokeOpacity={0.55}
          strokeDasharray="4 3"
          fill="var(--color-forecast)"
          fillOpacity={0.06}
          connectNulls={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ChartContainer>
  );
}

function MonthlyChart({ data: _data }: { data: MonthlyBucketsResponse }) {
  // Implemented in Task 13.
  return null;
}
