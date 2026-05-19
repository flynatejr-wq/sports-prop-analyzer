"use client";
import { TrendingUp, Target, AlertTriangle, BarChart2 } from "lucide-react";
import { useAnalyticsSummary } from "@/hooks/useProps";
import { clsx } from "clsx";

interface StatTileProps {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  color: string;
  loading?: boolean;
}

function StatTile({ label, value, sub, icon: Icon, color, loading }: StatTileProps) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 flex items-start gap-3">
      <div className={clsx("p-2.5 rounded-lg", color)}>
        <Icon size={18} className="opacity-90" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-muted text-xs mb-1">{label}</p>
        {loading ? (
          <div className="h-6 w-20 bg-surface-2 rounded animate-pulse" />
        ) : (
          <p className="text-white text-xl font-bold">{value}</p>
        )}
        {sub && <p className="text-muted text-xs mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function StatsOverview() {
  const { data: summary, isLoading } = useAnalyticsSummary();

  const tiles = [
    {
      label: "Active Props",
      value: summary?.active_props ?? 0,
      sub: `${summary?.high_ev_props ?? 0} high EV`,
      icon: Target,
      color: "bg-primary/20 text-primary",
    },
    {
      label: "Win Rate",
      value: summary ? `${summary.hit_rate}%` : "—",
      sub: `${summary?.wins ?? 0}W / ${summary?.losses ?? 0}L`,
      icon: TrendingUp,
      color: "bg-success/20 text-success",
    },
    {
      label: "ROI",
      value: summary ? `${summary.roi_pct > 0 ? "+" : ""}${summary.roi_pct}%` : "—",
      sub: `${summary?.total_profit_units ?? 0} units P/L`,
      icon: BarChart2,
      color: summary && summary.roi_pct > 0 ? "bg-success/20 text-success" : "bg-danger/20 text-danger",
    },
    {
      label: "Stale Lines",
      value: summary?.stale_lines ?? 0,
      sub: "potential value",
      icon: AlertTriangle,
      color: "bg-warning/20 text-warning",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {tiles.map((t) => (
        <StatTile key={t.label} {...t} loading={isLoading} />
      ))}
    </div>
  );
}
