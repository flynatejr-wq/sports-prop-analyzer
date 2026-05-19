"use client";
import useSWR from "swr";
import { getAnalyticsSummary, getHitRates, getPicks } from "@/lib/api";
import HitRateChart from "@/components/charts/HitRateChart";
import { TrendingUp, TrendingDown, BarChart2, Target } from "lucide-react";
import { clsx } from "clsx";
import { format, parseISO } from "date-fns";

export default function AnalyticsPage() {
  const { data: summary, isLoading: loadingSum } = useSWR("summary", getAnalyticsSummary);
  const { data: hitRates = [], isLoading: loadingHR } = useSWR("hit-rates", () => getHitRates());
  const { data: picks = [], isLoading: loadingPicks } = useSWR("picks", getPicks);

  const totalProfit = picks.reduce((s, p) => s + (p.profit_loss ?? 0), 0);
  const totalStaked = picks.reduce((s, p) => s + p.stake, 0);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-muted text-sm mt-1">Historical performance and betting insights</p>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Total Picks",
            value: summary?.picks_tracked ?? 0,
            icon: Target,
            color: "bg-primary/20 text-primary",
          },
          {
            label: "Win Rate",
            value: `${summary?.hit_rate ?? 0}%`,
            icon: TrendingUp,
            color: summary && summary.hit_rate > 52 ? "bg-success/20 text-success" : "bg-danger/20 text-danger",
          },
          {
            label: "P/L (units)",
            value: `${totalProfit >= 0 ? "+" : ""}${totalProfit.toFixed(2)}`,
            icon: totalProfit >= 0 ? TrendingUp : TrendingDown,
            color: totalProfit >= 0 ? "bg-success/20 text-success" : "bg-danger/20 text-danger",
          },
          {
            label: "ROI",
            value: totalStaked > 0 ? `${((totalProfit / totalStaked) * 100).toFixed(1)}%` : "—",
            icon: BarChart2,
            color: "bg-primary/20 text-primary",
          },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
            <div className={clsx("p-2.5 rounded-lg", color)}>
              <Icon size={18} />
            </div>
            <div>
              <p className="text-muted text-xs">{label}</p>
              <p className="text-white text-xl font-bold">{loadingSum ? "…" : value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {loadingHR ? (
          <div className="h-80 bg-surface border border-border rounded-xl animate-pulse" />
        ) : (
          <HitRateChart data={hitRates} />
        )}

        {/* Picks log */}
        <div className="bg-surface border border-border rounded-xl p-4">
          <h3 className="text-white font-semibold text-sm mb-4">Recent Picks</h3>
          {loadingPicks ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-10 bg-surface-2 rounded animate-pulse" />
              ))}
            </div>
          ) : picks.length === 0 ? (
            <p className="text-muted text-sm text-center py-8">No picks tracked yet</p>
          ) : (
            <div className="space-y-2 overflow-auto max-h-64">
              {picks.map((pick) => (
                <div
                  key={pick.id}
                  className="flex items-center gap-3 px-3 py-2 bg-surface-2 rounded-lg text-xs"
                >
                  <span className={clsx(
                    "px-2 py-0.5 rounded font-bold",
                    pick.direction === "over"
                      ? "bg-success/20 text-success"
                      : "bg-danger/20 text-danger"
                  )}>
                    {pick.direction.toUpperCase()}
                  </span>
                  <span className="text-muted flex-1">Prop #{pick.prop_id}</span>
                  <span className="text-white font-mono">{pick.stake}u</span>
                  <span className={clsx(
                    "font-mono font-bold",
                    pick.result === "hit" ? "text-success" :
                    pick.result === "miss" ? "text-danger" : "text-muted"
                  )}>
                    {pick.result === "pending" ? "—" :
                     pick.result === "hit" ? `+${pick.profit_loss?.toFixed(2)}` :
                     pick.profit_loss?.toFixed(2)}
                  </span>
                  <span className="text-muted opacity-60">
                    {pick.created_at ? format(parseISO(pick.created_at), "MM/dd") : ""}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
