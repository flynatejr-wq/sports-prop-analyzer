"use client";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine
} from "recharts";
import type { Prop } from "@/lib/types";

interface EVChartProps {
  props: Prop[];
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface-2 border border-border rounded-lg p-3 shadow-xl">
      <p className="text-white font-semibold text-xs mb-1">{d.name}</p>
      <p className="text-muted text-xs">{d.stat_type}</p>
      <p className="text-xs mt-1">
        <span className="text-muted">EV: </span>
        <span className={d.ev > 0 ? "text-ev-good font-bold" : "text-ev-negative"}>
          {d.ev > 0 ? "+" : ""}{d.ev.toFixed(1)}%
        </span>
      </p>
      <p className="text-xs">
        <span className="text-muted">Line: </span>
        <span className="text-white">{d.line}</span>
      </p>
    </div>
  );
};

export default function EVChart({ props }: EVChartProps) {
  const data = props
    .slice(0, 20)
    .map((p) => ({
      name: p.player_name.split(" ").pop() ?? p.player_name,
      fullName: p.player_name,
      stat_type: p.stat_type,
      line: p.line,
      ev: Math.max(p.ev_over ?? 0, p.ev_under ?? 0),
      direction: (p.ev_over ?? 0) >= (p.ev_under ?? 0) ? "OVER" : "UNDER",
    }))
    .sort((a, b) => b.ev - a.ev);

  const getColor = (ev: number) => {
    if (ev >= 15) return "#00ff87";
    if (ev >= 10) return "#22d3ee";
    if (ev >= 5) return "#60a5fa";
    if (ev >= 2) return "#a78bfa";
    return "#6b7280";
  };

  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <h3 className="text-white font-semibold text-sm mb-4">EV Distribution — Top 20 Props</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 0, right: 4, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fill: "#6b7280", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(99,102,241,0.08)" }} />
          <ReferenceLine y={5} stroke="#6366f1" strokeDasharray="4 2" strokeWidth={1} />
          <Bar dataKey="ev" radius={[4, 4, 0, 0]} maxBarSize={28}>
            {data.map((entry, i) => (
              <Cell key={i} fill={getColor(entry.ev)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 mt-2 justify-end">
        {[
          { color: "#00ff87", label: "Elite (15%+)" },
          { color: "#22d3ee", label: "Strong (10%+)" },
          { color: "#60a5fa", label: "Good (5%+)" },
          { color: "#a78bfa", label: "Slight (2%+)" },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ background: color }} />
            <span className="text-[10px] text-muted">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
