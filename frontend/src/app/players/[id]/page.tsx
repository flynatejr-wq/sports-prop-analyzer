"use client";
import { use, useState } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, TrendingUp, TrendingDown, BarChart2,
  Activity, Flame, Snowflake, Minus, Target, Calendar,
} from "lucide-react";
import { clsx } from "clsx";
import PropCard from "@/components/props/PropCard";
import type { Prop } from "@/lib/types";

// ── Fetch helpers ─────────────────────────────────────────────────────────────

async function fetchPlayer(id: string) {
  const res = await fetch(`/api/v1/players/${id}`);
  if (!res.ok) throw new Error("Player not found");
  return res.json();
}

async function fetchPlayerProps(id: string): Promise<Prop[]> {
  const res = await fetch(`/api/v1/players/${id}/props`);
  if (!res.ok) return [];
  const data = await res.json();
  // Props from this endpoint are partial; map to full Prop shape
  return data.map((p: Record<string, unknown>) => ({
    ...p,
    player_name: "",   // will be filled from player data
    sport: "NBA",
    team: null,
    is_stale: p.is_stale ?? false,
    is_boosted: false,
    status: "active",
  })) as Prop[];
}

async function fetchAnalytics(id: string, statType: string) {
  const res = await fetch(`/api/v1/players/${id}/analytics?stat_type=${encodeURIComponent(statType)}`);
  if (!res.ok) return null;
  return res.json();
}

// ── Sub-components ────────────────────────────────────────────────────────────

const SPORT_COLORS: Record<string, string> = {
  NBA:  "bg-orange-500/20 text-orange-400",
  NFL:  "bg-blue-500/20 text-blue-400",
  MLB:  "bg-red-500/20 text-red-400",
  NHL:  "bg-cyan-500/20 text-cyan-400",
};

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "HOT")     return <Flame size={14} className="text-danger" />;
  if (trend === "COLD")    return <Snowflake size={14} className="text-blue-400" />;
  return <Minus size={14} className="text-muted" />;
}

function StatBar({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="w-20 text-right text-xs text-muted flex-shrink-0">{label}</div>
      <div className="flex-1 h-2 bg-surface-2 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary/70 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-left text-xs text-white font-mono">{value.toFixed(1)}</span>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PlayerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [selectedStat, setSelectedStat] = useState("points");

  const { data: player, isLoading: playerLoading } = useSWR(
    `player-${id}`, () => fetchPlayer(id)
  );
  const { data: rawProps = [], isLoading: propsLoading } = useSWR(
    `player-props-${id}`, () => fetchPlayerProps(id), { refreshInterval: 60000 }
  );
  const { data: analytics } = useSWR(
    player ? `analytics-${id}-${selectedStat}` : null,
    () => fetchAnalytics(id, selectedStat),
    { revalidateOnFocus: false }
  );

  // Enrich props with player name
  const props: Prop[] = rawProps.map((p) => ({
    ...p,
    player_name: player?.name ?? "",
    sport: player?.sport ?? "NBA",
    team: player?.team ?? null,
    image_url: player?.image_url ?? null,
  }));

  // Derive available stat types from props
  const statTypes = Array.from(new Set(props.map((p) => p.stat_type.toLowerCase())));

  if (playerLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="h-8 w-32 bg-surface rounded animate-pulse" />
        <div className="h-40 bg-surface border border-border rounded-xl animate-pulse" />
      </div>
    );
  }

  if (!player) {
    return (
      <div className="text-center py-20">
        <p className="text-white font-medium">Player not found</p>
        <button onClick={() => router.back()} className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm">
          Go Back
        </button>
      </div>
    );
  }

  const bestPropEv = props.length > 0
    ? Math.max(...props.map((p) => Math.max(p.ev_over ?? 0, p.ev_under ?? 0)))
    : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Breadcrumb */}
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-muted text-sm hover:text-white transition-colors">
          <ArrowLeft size={16} /> Back
        </button>
        <span className="text-border">/</span>
        <a href="/players" className="text-muted text-sm hover:text-white transition-colors">Players</a>
        <span className="text-border">/</span>
        <span className="text-white text-sm font-medium">{player.name}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Left column ───────────────────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-5">

          {/* Player hero */}
          <div className="bg-surface border border-border rounded-xl p-6">
            <div className="flex items-start gap-5">
              {player.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={player.image_url}
                  alt={player.name}
                  className="w-20 h-20 rounded-full object-cover bg-surface-2 ring-2 ring-border flex-shrink-0"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary/40 to-primary/10 flex-shrink-0 flex items-center justify-center text-2xl font-bold text-primary ring-2 ring-border">
                  {player.name.charAt(0)}
                </div>
              )}

              <div className="flex-1 min-w-0">
                <h1 className="text-white text-2xl font-bold">{player.name}</h1>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span className={clsx("text-xs font-bold px-2 py-0.5 rounded", SPORT_COLORS[player.sport] ?? "bg-surface-2 text-muted")}>
                    {player.sport}
                  </span>
                  {player.team && <span className="text-muted text-sm">{player.team}</span>}
                  {player.position && <span className="text-muted text-sm">· {player.position}</span>}
                  {player.injury_status && player.injury_status !== "active" && (
                    <span className="px-2 py-0.5 bg-danger/20 text-danger border border-danger/30 rounded text-xs font-semibold">
                      {player.injury_status.toUpperCase()}
                    </span>
                  )}
                </div>
                {player.injury_note && (
                  <p className="text-muted text-xs mt-2 italic">{player.injury_note}</p>
                )}
              </div>

              {/* Best EV pill */}
              {bestPropEv > 0 && (
                <div className="flex-shrink-0 px-4 py-2 bg-ev-good/10 border border-ev-good/30 rounded-xl text-center">
                  <p className="text-ev-good text-xl font-bold font-mono">+{bestPropEv.toFixed(1)}%</p>
                  <p className="text-muted text-[10px]">Best EV</p>
                </div>
              )}
            </div>
          </div>

          {/* Analytics section */}
          {statTypes.length > 0 && (
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <BarChart2 size={16} className="text-primary" />
                <h3 className="text-white font-semibold text-sm">Performance Analytics</h3>
              </div>

              {/* Stat type tabs */}
              <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg mb-4 flex-wrap">
                {statTypes.map((s) => (
                  <button
                    key={s}
                    onClick={() => setSelectedStat(s)}
                    className={clsx(
                      "px-3 py-1.5 rounded text-xs font-medium transition-all capitalize",
                      selectedStat === s ? "bg-primary text-white" : "text-muted hover:text-white"
                    )}
                  >
                    {s}
                  </button>
                ))}
              </div>

              {analytics ? (
                <div className="space-y-4">
                  {/* KPI row */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { label: "Season Avg", value: analytics.season_avg?.toFixed(1) ?? "—" },
                      { label: "Last 5 Avg",  value: analytics.last_5_avg?.toFixed(1)  ?? "—" },
                      { label: "Last 10 Avg", value: analytics.last_10_avg?.toFixed(1) ?? "—" },
                      { label: "Games",       value: analytics.games_played ?? 0 },
                    ].map(({ label, value }) => (
                      <div key={label} className="bg-surface-2 rounded-xl p-3 text-center">
                        <p className="text-muted text-xs">{label}</p>
                        <p className="text-white font-bold text-lg font-mono">{value}</p>
                      </div>
                    ))}
                  </div>

                  {/* Trend + H/A split */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-surface-2 rounded-xl p-4">
                      <p className="text-muted text-xs mb-2">Current Trend</p>
                      <div className="flex items-center gap-2">
                        <TrendIcon trend={analytics.trend} />
                        <span className={clsx(
                          "font-semibold",
                          analytics.trend === "HOT"  ? "text-danger" :
                          analytics.trend === "COLD" ? "text-blue-400" : "text-muted"
                        )}>
                          {analytics.trend}
                        </span>
                      </div>
                    </div>
                    <div className="bg-surface-2 rounded-xl p-4">
                      <p className="text-muted text-xs mb-2">Home / Away Split</p>
                      {analytics.home_avg != null && analytics.away_avg != null ? (
                        <div className="space-y-1.5">
                          <StatBar value={analytics.home_avg} max={analytics.season_avg * 1.5} label="Home" />
                          <StatBar value={analytics.away_avg} max={analytics.season_avg * 1.5} label="Away" />
                        </div>
                      ) : (
                        <p className="text-muted text-xs">Not enough data</p>
                      )}
                    </div>
                  </div>

                  {/* Recent game log */}
                  {analytics.recent_games?.length > 0 && (
                    <div>
                      <p className="text-muted text-xs mb-2">Recent Games</p>
                      <div className="space-y-1">
                        {analytics.recent_games.slice(0, 8).map((g: Record<string, unknown>, i: number) => {
                          const val = g.value as number | null;
                          const line = props.find((p) => p.stat_type.toLowerCase() === selectedStat)?.line;
                          const hitOver = line != null && val != null && val > line;
                          return (
                            <div key={i} className="flex items-center gap-3 px-3 py-2 bg-surface-2 rounded-lg text-xs">
                              <div className="flex items-center gap-1 text-muted w-20 flex-shrink-0">
                                <Calendar size={10} />
                                <span>{g.game_date as string ?? "—"}</span>
                              </div>
                              <span className="text-muted flex-1">{(g.is_home as boolean) ? "HOME" : "AWAY"} vs {(g.opponent as string) ?? "—"}</span>
                              <span className={clsx(
                                "font-mono font-bold",
                                line != null
                                  ? hitOver ? "text-success" : "text-danger"
                                  : "text-white"
                              )}>
                                {val?.toFixed(1) ?? "—"}
                              </span>
                              {line != null && (
                                <span className={clsx(
                                  "w-14 text-right text-[10px] font-semibold",
                                  hitOver ? "text-success" : "text-danger"
                                )}>
                                  {hitOver ? "▲ OVER" : "▼ UNDER"}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-32 bg-surface-2 rounded-xl animate-pulse" />
              )}
            </div>
          )}

          {/* Active props */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Target size={16} className="text-primary" />
              <h3 className="text-white font-semibold text-sm">
                Active Props ({propsLoading ? "…" : props.length})
              </h3>
            </div>

            {propsLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-64 bg-surface border border-border rounded-xl animate-pulse" />
                ))}
              </div>
            ) : props.length === 0 ? (
              <div className="text-center py-10 bg-surface border border-border rounded-xl">
                <Activity size={28} className="text-muted mx-auto mb-2 opacity-40" />
                <p className="text-muted text-sm">No active props right now</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {props.map((p) => (
                  <PropCard key={p.id} prop={p} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Right sidebar ─────────────────────────────────────────────── */}
        <div className="space-y-5">
          {/* Player info card */}
          <div className="bg-surface border border-border rounded-xl p-5 space-y-3">
            <h3 className="text-white font-semibold text-sm">Player Info</h3>
            {[
              { label: "Sport",    value: player.sport },
              { label: "Team",     value: player.team ?? "—" },
              { label: "Position", value: player.position ?? "—" },
              { label: "Status",   value: player.injury_status ?? "Active", highlight: player.injury_status && player.injury_status !== "active" },
              { label: "Active Props", value: props.length },
              { label: "Best EV",  value: bestPropEv > 0 ? `+${bestPropEv.toFixed(2)}%` : "—" },
            ].map(({ label, value, highlight }) => (
              <div key={label} className="flex justify-between items-center text-xs border-b border-border/40 pb-2 last:border-0 last:pb-0">
                <span className="text-muted">{label}</span>
                <span className={clsx("font-medium", highlight ? "text-danger" : "text-white")}>
                  {String(value)}
                </span>
              </div>
            ))}
          </div>

          {/* EV summary by prop */}
          {props.length > 0 && (
            <div className="bg-surface border border-border rounded-xl p-5">
              <h3 className="text-white font-semibold text-sm mb-3">Props EV Breakdown</h3>
              <div className="space-y-2">
                {props.map((p) => {
                  const ev = Math.max(p.ev_over ?? 0, p.ev_under ?? 0);
                  const dir = (p.ev_over ?? 0) >= (p.ev_under ?? 0) ? "OVER" : "UNDER";
                  const evColor = ev >= 10 ? "text-ev-elite" : ev >= 5 ? "text-ev-strong" : ev >= 2 ? "text-ev-good" : "text-muted";
                  return (
                    <a
                      key={p.id}
                      href={`/props/${p.id}`}
                      className="flex items-center justify-between gap-2 px-3 py-2 bg-surface-2 rounded-lg hover:bg-surface-3 transition-colors"
                    >
                      <div>
                        <p className="text-white text-xs font-medium">{p.stat_type}</p>
                        <p className="text-muted text-[10px]">Line: {p.line}</p>
                      </div>
                      <div className="text-right">
                        <p className={clsx("text-xs font-bold font-mono", evColor)}>
                          {ev > 0 ? `+${ev.toFixed(1)}%` : "—"}
                        </p>
                        <div className="flex items-center justify-end gap-0.5">
                          {dir === "OVER"
                            ? <TrendingUp size={10} className="text-success" />
                            : <TrendingDown size={10} className="text-danger" />}
                          <span className="text-[10px] text-muted">{dir}</span>
                        </div>
                      </div>
                    </a>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
