"use client";
import { useState } from "react";
import useSWR from "swr";
import { getAnalyticsSummary, getHitRates, getPicks } from "@/lib/api";
import HitRateChart from "@/components/charts/HitRateChart";
import { TrendingUp, TrendingDown, BarChart2, Target, CheckCircle, XCircle, Trash2, Trophy } from "lucide-react";
import { clsx } from "clsx";
import { format, parseISO } from "date-fns";
import { useNotificationStore } from "@/store";

// ── Pick result settle ────────────────────────────────────────────────────────

async function settlePick(id: number, result: "hit" | "miss") {
  const res = await fetch(`/api/v1/analytics/picks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result }),
  });
  if (!res.ok) throw new Error("Failed to settle pick");
  return res.json();
}

async function deletePick(id: number) {
  const res = await fetch(`/api/v1/analytics/picks/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete");
}

// ── Picks table ───────────────────────────────────────────────────────────────

function PicksTable() {
  const { addToast } = useNotificationStore();
  const { data: picks = [], isLoading, mutate } = useSWR("picks", getPicks, { refreshInterval: 30000 });
  const [acting, setActing] = useState<number | null>(null);

  async function handleSettle(id: number, result: "hit" | "miss") {
    setActing(id);
    try {
      await settlePick(id, result);
      addToast({ type: result === "hit" ? "success" : "warning", title: `Pick marked ${result}` });
      await mutate();
    } catch {
      addToast({ type: "error", title: "Failed to settle pick" });
    } finally {
      setActing(null);
    }
  }

  async function handleDelete(id: number) {
    setActing(id);
    try {
      await deletePick(id);
      addToast({ type: "info", title: "Pick removed" });
      await mutate();
    } catch {
      addToast({ type: "error", title: "Failed to delete pick" });
    } finally {
      setActing(null);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 bg-surface-2 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (picks.length === 0) {
    return (
      <div className="text-center py-10">
        <Trophy size={28} className="text-muted mx-auto mb-2 opacity-40" />
        <p className="text-muted text-sm">No picks tracked yet</p>
        <p className="text-muted text-xs mt-1">Click "Track this Pick" on any prop card</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border">
            {["Prop", "Direction", "Stake", "EV", "Result", "P/L", "Date", ""].map((h) => (
              <th key={h} className="px-3 py-2 text-left text-muted font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {picks.map((pick) => (
            <tr key={pick.id} className="border-b border-border/40 hover:bg-surface-2/30 transition-colors">
              <td className="px-3 py-2.5">
                <a href={`/props/${pick.prop_id}`} className="text-primary hover:underline">
                  #{pick.prop_id}
                </a>
              </td>
              <td className="px-3 py-2.5">
                <span className={clsx(
                  "px-2 py-0.5 rounded font-bold",
                  pick.direction === "over"
                    ? "bg-success/20 text-success"
                    : "bg-danger/20 text-danger"
                )}>
                  {pick.direction.toUpperCase()}
                </span>
              </td>
              <td className="px-3 py-2.5 font-mono text-white">{pick.stake}u</td>
              <td className="px-3 py-2.5 font-mono text-primary">
                {pick.ev_at_pick != null ? `+${pick.ev_at_pick.toFixed(1)}%` : "—"}
              </td>
              <td className="px-3 py-2.5">
                {pick.result === "pending" ? (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleSettle(pick.id, "hit")}
                      disabled={acting === pick.id}
                      className="flex items-center gap-1 px-2 py-1 bg-success/20 border border-success/30 text-success rounded hover:bg-success/30 transition-colors disabled:opacity-50"
                    >
                      <CheckCircle size={11} /> Hit
                    </button>
                    <button
                      onClick={() => handleSettle(pick.id, "miss")}
                      disabled={acting === pick.id}
                      className="flex items-center gap-1 px-2 py-1 bg-danger/20 border border-danger/30 text-danger rounded hover:bg-danger/30 transition-colors disabled:opacity-50"
                    >
                      <XCircle size={11} /> Miss
                    </button>
                  </div>
                ) : (
                  <span className={clsx(
                    "flex items-center gap-1 font-semibold",
                    pick.result === "hit" ? "text-success" : "text-danger"
                  )}>
                    {pick.result === "hit"
                      ? <><CheckCircle size={11} /> HIT</>
                      : <><XCircle size={11} /> MISS</>}
                  </span>
                )}
              </td>
              <td className="px-3 py-2.5 font-mono font-bold">
                {pick.result === "pending" ? (
                  <span className="text-muted">—</span>
                ) : (
                  <span className={pick.profit_loss != null && pick.profit_loss >= 0 ? "text-success" : "text-danger"}>
                    {pick.profit_loss != null
                      ? `${pick.profit_loss >= 0 ? "+" : ""}${pick.profit_loss.toFixed(2)}u`
                      : "—"}
                  </span>
                )}
              </td>
              <td className="px-3 py-2.5 text-muted">
                {pick.created_at ? format(parseISO(pick.created_at), "MM/dd HH:mm") : "—"}
              </td>
              <td className="px-3 py-2.5">
                <button
                  onClick={() => handleDelete(pick.id)}
                  disabled={acting === pick.id}
                  className="p-1 text-muted hover:text-danger transition-colors disabled:opacity-50 rounded"
                >
                  <Trash2 size={12} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const { data: summary, isLoading: loadingSum } = useSWR("summary", getAnalyticsSummary);
  const { data: hitRates = [], isLoading: loadingHR } = useSWR("hit-rates", () => getHitRates());
  const [activeSection, setActiveSection] = useState<"picks" | "hit-rates">("picks");

  const totalProfit = summary?.total_profit_units ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-muted text-sm mt-1">Performance tracking and betting insights</p>
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
            sub: `${summary?.wins ?? 0}W / ${summary?.losses ?? 0}L`,
          },
          {
            label: "P/L (units)",
            value: `${totalProfit >= 0 ? "+" : ""}${totalProfit.toFixed(2)}`,
            icon: totalProfit >= 0 ? TrendingUp : TrendingDown,
            color: totalProfit >= 0 ? "bg-success/20 text-success" : "bg-danger/20 text-danger",
          },
          {
            label: "ROI",
            value: summary ? `${summary.roi_pct > 0 ? "+" : ""}${summary.roi_pct}%` : "—",
            icon: BarChart2,
            color: summary && summary.roi_pct > 0 ? "bg-success/20 text-success" : "bg-primary/20 text-primary",
          },
        ].map(({ label, value, icon: Icon, color, sub }) => (
          <div key={label} className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
            <div className={clsx("p-2.5 rounded-lg", color)}>
              <Icon size={18} />
            </div>
            <div>
              <p className="text-muted text-xs">{label}</p>
              <p className="text-white text-xl font-bold">{loadingSum ? "…" : value}</p>
              {sub && <p className="text-muted text-xs">{sub}</p>}
            </div>
          </div>
        ))}
      </div>

      {/* Section tabs */}
      <div className="flex items-center gap-1 bg-surface border border-border p-1 rounded-xl w-fit">
        {([
          { id: "picks" as const,     label: "My Picks",   icon: Target    },
          { id: "hit-rates" as const, label: "Hit Rates",  icon: BarChart2 },
        ]).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveSection(id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              activeSection === id ? "bg-primary text-white" : "text-muted hover:text-white"
            )}
          >
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeSection === "picks" ? (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="text-white font-semibold text-sm mb-4">Tracked Picks</h3>
          <PicksTable />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {loadingHR ? (
            <div className="h-80 bg-surface border border-border rounded-xl animate-pulse" />
          ) : (
            <HitRateChart data={hitRates} />
          )}

          {/* Stat breakdown table */}
          <div className="bg-surface border border-border rounded-xl p-4">
            <h3 className="text-white font-semibold text-sm mb-4">Hit Rate by Stat Type</h3>
            {loadingHR ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="h-8 bg-surface-2 rounded animate-pulse" />
                ))}
              </div>
            ) : hitRates.length === 0 ? (
              <p className="text-muted text-sm text-center py-8">No settled props yet</p>
            ) : (
              <div className="space-y-2 overflow-y-auto max-h-64">
                {hitRates.map((row) => (
                  <div key={row.stat_type} className="flex items-center gap-3">
                    <span className="text-muted text-xs w-32 truncate flex-shrink-0">{row.stat_type}</span>
                    <div className="flex-1 h-2 bg-surface-2 rounded-full overflow-hidden">
                      <div
                        className={clsx(
                          "h-full rounded-full transition-all",
                          row.hit_rate >= 60 ? "bg-success" :
                          row.hit_rate >= 50 ? "bg-primary" : "bg-danger"
                        )}
                        style={{ width: `${row.hit_rate}%` }}
                      />
                    </div>
                    <span className="text-white text-xs font-mono w-12 text-right">{row.hit_rate}%</span>
                    <span className="text-muted text-[10px] w-14 text-right">{row.total} settled</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
