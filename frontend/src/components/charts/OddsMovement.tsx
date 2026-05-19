"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine
} from "recharts";
import { format, parseISO } from "date-fns";
import type { OddsMovement } from "@/lib/types";

interface OddsMovementChartProps {
  data: OddsMovement[];
  ppLine: number;
  title?: string;
}

export default function OddsMovementChart({ data, ppLine, title }: OddsMovementChartProps) {
  const chartData = data.map((d) => ({
    time: d.timestamp ? format(parseISO(d.timestamp), "HH:mm") : "",
    line: d.line,
    sportsbook: d.sportsbook,
  }));

  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <h3 className="text-white font-semibold text-sm mb-4">
        {title ?? "Line Movement"}
      </h3>
      {data.length === 0 ? (
        <div className="flex items-center justify-center h-40 text-muted text-sm">
          No movement data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="time"
              tick={{ fill: "#6b7280", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#6b7280", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                background: "#111827",
                border: "1px solid #1f2937",
                borderRadius: "8px",
                fontSize: "11px",
                color: "#e2e8f0",
              }}
            />
            <ReferenceLine y={ppLine} stroke="#f59e0b" strokeDasharray="4 2" label={{
              value: `PP: ${ppLine}`,
              fill: "#f59e0b",
              fontSize: 10,
              position: "insideTopRight",
            }} />
            <Line
              type="monotone"
              dataKey="line"
              stroke="#6366f1"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#6366f1" }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
      <p className="text-muted text-xs mt-2 text-center">
        Yellow dashed = PrizePicks line • Purple = sportsbook consensus
      </p>
    </div>
  );
}
