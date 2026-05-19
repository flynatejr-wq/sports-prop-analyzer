"use client";
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Cell
} from "recharts";
import type { HitRateRow } from "@/lib/types";

interface HitRateChartProps {
  data: HitRateRow[];
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as HitRateRow;
  return (
    <div className="bg-surface-2 border border-border rounded-lg p-3 shadow-xl text-xs">
      <p className="text-white font-semibold mb-1">{d.stat_type}</p>
      <p className="text-muted">Hit Rate: <span className="text-success font-bold">{d.hit_rate}%</span></p>
      <p className="text-muted">Total: {d.total} props | Wins: {d.hits}</p>
      <p className="text-muted">Avg EV: {d.avg_ev > 0 ? "+" : ""}{d.avg_ev}%</p>
    </div>
  );
};

export default function HitRateChart({ data }: HitRateChartProps) {
  const sorted = [...data].sort((a, b) => b.hit_rate - a.hit_rate).slice(0, 10);

  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <h3 className="text-white font-semibold text-sm mb-4">Historical Hit Rates by Stat Type</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={sorted} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: "#6b7280", fontSize: 10 }}
            tickFormatter={(v) => `${v}%`}
            axisLine={false}
            tickLine={false}
            domain={[0, 100]}
          />
          <YAxis
            type="category"
            dataKey="stat_type"
            tick={{ fill: "#94a3b8", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(99,102,241,0.08)" }} />
          <Bar dataKey="hit_rate" radius={[0, 4, 4, 0]} maxBarSize={16}>
            {sorted.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.hit_rate >= 60 ? "#10b981" : entry.hit_rate >= 50 ? "#6366f1" : "#374151"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
