"use client";
import { useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus, Zap, AlertTriangle, RefreshCw } from "lucide-react";
import { clsx } from "clsx";
import { format, parseISO } from "date-fns";
import OddsMovementChart from "@/components/charts/OddsMovement";
import { getOddsMovement } from "@/lib/api";
import { StaggerChildren, StaggerItem, FadeIn } from "@/components/ui/AnimatedCard";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchMovements(hours: number, sport?: string, minMovement?: number) {
  const q = new URLSearchParams({ hours: String(hours) });
  if (sport) q.set("sport", sport);
  if (minMovement) q.set("min_movement", String(minMovement));
  const res = await fetch(`${BASE}/api/v1/line-movement/recent?${q}`);
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
}

async function fetchSteamMoves() {
  const res = await fetch(`${BASE}/api/v1/line-movement/steam-moves`);
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
}

const HOURS_OPTIONS = [1, 2, 4, 8, 24];
const SPORTS = ["All", "NBA", "NFL", "MLB", "NHL"];

export default function LineMovementPage() {
  const [hours, setHours] = useState(4);
  const [sport, setSport] = useState("All");
  const [selectedProp, setSelectedProp] = useState<number | null>(null);
  const [tab, setTab] = useState<"all" | "steam">("all");

  const { data: movements = [], isLoading, mutate } = useSWR(
    ["movements", hours, sport, tab],
    () =>
      tab === "steam"
        ? fetchSteamMoves()
        : fetchMovements(hours, sport !== "All" ? sport : undefined),
    { refreshInterval: 30000 }
  );

  const { data: propMovement = [] } = useSWR(
    selectedProp ? ["prop-movement", selectedProp] : null,
    () => getOddsMovement(selectedProp!),
    { refreshInterval: 60000 }
  );

  return (
    <FadeIn className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Line Movement</h1>
          <p className="text-muted text-sm mt-1">Track sharp action and steam moves in real time</p>
        </div>
        <button
          onClick={() => mutate()}
          className="flex items-center gap-2 px-3 py-1.5 bg-surface-2 border border-border rounded-lg text-xs text-muted hover:text-white transition-colors"
        >
          <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-surface border border-border p-1 rounded-xl w-fit">
        {(["all", "steam"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              tab === t ? "bg-primary text-white" : "text-muted hover:text-white"
            )}
          >
            {t === "steam" ? <Zap size={14} /> : <TrendingUp size={14} />}
            {t === "all" ? "All Movements" : "Steam Moves"}
            {t === "steam" && movements.filter((m: any) => m.is_steam).length > 0 && (
              <span className="ml-1 w-4 h-4 rounded-full bg-danger text-white text-[10px] flex items-center justify-center">
                {movements.filter((m: any) => m.is_steam).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Filters */}
      {tab === "all" && (
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg">
            {HOURS_OPTIONS.map((h) => (
              <button
                key={h}
                onClick={() => setHours(h)}
                className={clsx(
                  "px-2.5 py-1 rounded text-xs font-medium transition-all",
                  hours === h ? "bg-primary text-white" : "text-muted hover:text-white"
                )}
              >
                {h}h
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg">
            {SPORTS.map((s) => (
              <button
                key={s}
                onClick={() => setSport(s)}
                className={clsx(
                  "px-2.5 py-1 rounded text-xs font-medium transition-all",
                  sport === s ? "bg-primary text-white" : "text-muted hover:text-white"
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Movement list */}
        <div className="xl:col-span-2 space-y-2">
          {isLoading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-16 bg-surface border border-border rounded-xl animate-pulse" />
            ))
          ) : movements.length === 0 ? (
            <div className="text-center py-16">
              <TrendingUp size={36} className="text-muted mx-auto mb-3 opacity-40" />
              <p className="text-white font-medium">No significant line movement</p>
              <p className="text-muted text-sm mt-1">in the last {hours} hours</p>
            </div>
          ) : (
            <StaggerChildren>
              {movements.map((event: any) => (
                <StaggerItem key={event.prop_id}>
                  <button
                    onClick={() => setSelectedProp(
                      selectedProp === event.prop_id ? null : event.prop_id
                    )}
                    className={clsx(
                      "w-full text-left flex items-center gap-4 px-4 py-3 rounded-xl border transition-all",
                      selectedProp === event.prop_id
                        ? "bg-primary/10 border-primary/40"
                        : "bg-surface border-border hover:border-primary/30"
                    )}
                  >
                    {/* Direction indicator */}
                    <div className={clsx(
                      "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                      event.movement_direction === "UP" ? "bg-success/20 text-success" :
                      event.movement_direction === "DOWN" ? "bg-danger/20 text-danger" :
                      "bg-surface-2 text-muted"
                    )}>
                      {event.movement_direction === "UP" ? <TrendingUp size={14} /> :
                       event.movement_direction === "DOWN" ? <TrendingDown size={14} /> :
                       <Minus size={14} />}
                    </div>

                    {/* Player info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-white text-sm font-semibold truncate">
                          {event.player_name}
                        </p>
                        {event.is_steam && (
                          <span className="flex items-center gap-1 px-1.5 py-0.5 bg-danger/20 border border-danger/30 rounded text-[10px] text-danger font-bold flex-shrink-0">
                            <Zap size={9} />STEAM
                          </span>
                        )}
                      </div>
                      <p className="text-muted text-xs">{event.sport} • {event.stat_type}</p>
                    </div>

                    {/* Numbers */}
                    <div className="flex items-center gap-6 flex-shrink-0">
                      <div className="text-center">
                        <p className="text-muted text-[10px]">PP Line</p>
                        <p className="text-white font-mono font-bold text-sm">{event.pp_line}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-muted text-[10px]">Market</p>
                        <p className="text-white font-mono font-bold text-sm">{event.line}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-muted text-[10px]">Moved</p>
                        <p className={clsx(
                          "font-mono font-bold text-sm",
                          event.movement_direction === "UP" ? "text-success" :
                          event.movement_direction === "DOWN" ? "text-danger" : "text-muted"
                        )}>
                          {event.movement_direction === "UP" ? "+" : event.movement_direction === "DOWN" ? "-" : ""}
                          {event.movement_magnitude}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-muted text-[10px]">Discrepancy</p>
                        <p className={clsx(
                          "font-mono font-bold text-sm",
                          event.discrepancy < -0.5 ? "text-success" :
                          event.discrepancy > 0.5 ? "text-danger" : "text-muted"
                        )}>
                          {event.discrepancy > 0 ? "+" : ""}{event.discrepancy.toFixed(1)}
                        </p>
                      </div>
                    </div>
                  </button>
                </StaggerItem>
              ))}
            </StaggerChildren>
          )}
        </div>

        {/* Detail panel */}
        <div className="space-y-4">
          {selectedProp ? (
            <>
              <OddsMovementChart
                data={propMovement}
                ppLine={movements.find((m: any) => m.prop_id === selectedProp)?.pp_line ?? 0}
                title="Line Movement History"
              />
              <div className="bg-surface border border-border rounded-xl p-4">
                <h3 className="text-white font-semibold text-sm mb-3">Books Moving</h3>
                <div className="flex flex-wrap gap-2">
                  {(movements.find((m: any) => m.prop_id === selectedProp)?.books_moving ?? []).map((book: string) => (
                    <span key={book} className="px-2 py-1 bg-surface-2 border border-border rounded text-xs text-muted">
                      {book}
                    </span>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-surface border border-border rounded-xl p-6 text-center">
              <TrendingUp size={28} className="text-muted mx-auto mb-3 opacity-40" />
              <p className="text-muted text-sm">Select a prop to see line movement history</p>
            </div>
          )}

          {/* Legend */}
          <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
            <h3 className="text-white font-semibold text-sm mb-2">Reading Line Movement</h3>
            <div className="space-y-2 text-xs text-muted">
              <div className="flex items-start gap-2">
                <Zap size={12} className="text-danger mt-0.5 flex-shrink-0" />
                <p><span className="text-white font-medium">Steam Move:</span> Rapid ≥1 unit shift across multiple books — signals sharp/syndicate money</p>
              </div>
              <div className="flex items-start gap-2">
                <AlertTriangle size={12} className="text-warning mt-0.5 flex-shrink-0" />
                <p><span className="text-white font-medium">Discrepancy:</span> PrizePicks line vs sportsbook consensus — negative = value on OVER</p>
              </div>
              <div className="flex items-start gap-2">
                <TrendingUp size={12} className="text-success mt-0.5 flex-shrink-0" />
                <p><span className="text-white font-medium">Line UP:</span> Sharp money on the OVER pushed books to raise the line</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </FadeIn>
  );
}
