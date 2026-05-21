"use client";
import { useState, useMemo } from "react";
import useSWR from "swr";
import { Users, Search, TrendingUp, TrendingDown, BarChart2, ArrowRight } from "lucide-react";
import { clsx } from "clsx";
import { FadeIn } from "@/components/ui/AnimatedCard";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PlayerStat {
  id: number;
  player_name: string;
  team: string | null;
  sport: string;
  image_url: string | null;
  active_props: number;
  best_ev: number;
  best_direction: string;
  best_stat_type: string;
  best_line: number;
}

// ── Fetch ─────────────────────────────────────────────────────────────────────

async function fetchPlayers(): Promise<PlayerStat[]> {
  const res = await fetch("/api/v1/players/with-props?limit=100");
  if (!res.ok) return [];
  return res.json();
}

// ── Sport chip ────────────────────────────────────────────────────────────────

const SPORT_COLORS: Record<string, string> = {
  NBA:  "bg-orange-500/20 text-orange-400",
  NFL:  "bg-blue-500/20 text-blue-400",
  MLB:  "bg-red-500/20 text-red-400",
  NHL:  "bg-cyan-500/20 text-cyan-400",
  WNBA: "bg-purple-500/20 text-purple-400",
  NCAAB:"bg-yellow-500/20 text-yellow-400",
};

const SPORTS = ["ALL", "NBA", "NFL", "MLB", "NHL"];

// ── Player card ───────────────────────────────────────────────────────────────

function PlayerCard({ p }: { p: PlayerStat }) {
  const ev = p.best_ev;
  const evColor =
    ev >= 10 ? "text-ev-elite" :
    ev >= 5  ? "text-ev-strong" :
    ev >= 2  ? "text-ev-good" :
    ev > 0   ? "text-primary" :
    "text-muted";

  return (
    <a
      href={`/players/${p.id}`}
      className="group bg-surface border border-border hover:border-primary/40 rounded-xl p-4 flex items-center gap-4 transition-all hover:shadow-lg hover:shadow-primary/5"
    >
      {/* Avatar */}
      {p.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={p.image_url}
          alt={p.player_name}
          className="w-12 h-12 rounded-full object-cover bg-surface-2 ring-2 ring-border flex-shrink-0"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
      ) : (
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/30 to-primary/10 flex-shrink-0 flex items-center justify-center text-base font-bold text-primary ring-2 ring-border">
          {p.player_name.charAt(0)}
        </div>
      )}

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-white font-semibold text-sm truncate">{p.player_name}</p>
          <span className={clsx("text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0", SPORT_COLORS[p.sport] ?? "bg-surface-2 text-muted")}>
            {p.sport}
          </span>
        </div>
        <p className="text-muted text-xs mt-0.5">{p.team ?? "—"}</p>
        <p className="text-muted text-[10px] mt-1">
          {p.active_props} active prop{p.active_props !== 1 ? "s" : ""}
          {p.best_stat_type ? ` · ${p.best_stat_type} ${p.best_line}` : ""}
        </p>
      </div>

      {/* Best EV */}
      <div className="text-right flex-shrink-0">
        <div className="flex items-center justify-end gap-1 mb-1">
          {p.best_direction === "OVER"
            ? <TrendingUp size={11} className="text-success" />
            : <TrendingDown size={11} className="text-danger" />}
          <span className="text-muted text-[10px]">{p.best_direction}</span>
        </div>
        <p className={clsx("text-sm font-bold font-mono", evColor)}>
          {ev > 0 ? `+${ev.toFixed(1)}%` : `${ev.toFixed(1)}%`}
        </p>
        <p className="text-muted text-[10px]">Best EV</p>
      </div>

      <ArrowRight size={14} className="text-border group-hover:text-primary transition-colors flex-shrink-0" />
    </a>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PlayersPage() {
  const { data: players = [], isLoading } = useSWR("players-with-props", fetchPlayers, {
    refreshInterval: 60000,
  });

  const [query, setQuery] = useState("");
  const [sport, setSport] = useState("ALL");
  const [sortBy, setSortBy] = useState<"ev" | "props" | "name">("ev");

  const filtered = useMemo(() => {
    let list = players;
    if (query) {
      const q = query.toLowerCase();
      list = list.filter(
        (p) => p.player_name.toLowerCase().includes(q) || (p.team ?? "").toLowerCase().includes(q)
      );
    }
    if (sport !== "ALL") {
      list = list.filter((p) => p.sport === sport);
    }
    list = [...list].sort((a, b) => {
      if (sortBy === "ev")    return b.best_ev - a.best_ev;
      if (sortBy === "props") return b.active_props - a.active_props;
      return a.player_name.localeCompare(b.player_name);
    });
    return list;
  }, [players, query, sport, sortBy]);

  const totalEVPositive = players.filter((p) => p.best_ev > 0).length;

  return (
    <FadeIn className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Users size={20} className="text-primary" />
          <h1 className="text-2xl font-bold text-white">Players</h1>
        </div>
        <p className="text-muted text-sm mt-1">
          {players.length} tracked players · {totalEVPositive} with positive EV
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Players", value: players.length, icon: Users, color: "text-primary bg-primary/20" },
          { label: "With +EV Props", value: totalEVPositive, icon: TrendingUp, color: "text-success bg-success/20" },
          {
            label: "Best EV Available",
            value: players.length > 0 ? `+${Math.max(...players.map((p) => p.best_ev)).toFixed(1)}%` : "—",
            icon: BarChart2,
            color: "text-ev-elite bg-ev-elite/20",
          },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
            <div className={clsx("p-2.5 rounded-lg", color)}>
              <Icon size={18} />
            </div>
            <div>
              <p className="text-muted text-xs">{label}</p>
              <p className="text-white text-lg font-bold">{isLoading ? "…" : value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-48 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search players or teams..."
            className="w-full pl-9 pr-4 py-2 bg-surface-2 border border-border rounded-lg text-sm text-white placeholder-muted focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        {/* Sport filter */}
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

        {/* Sort */}
        <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg">
          {([
            { id: "ev",    label: "Best EV" },
            { id: "props", label: "Most Props" },
            { id: "name",  label: "Name" },
          ] as const).map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setSortBy(id)}
              className={clsx(
                "px-2.5 py-1 rounded text-xs font-medium transition-all",
                sortBy === id ? "bg-primary text-white" : "text-muted hover:text-white"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Player list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-20 bg-surface border border-border rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <Users size={40} className="text-muted mx-auto mb-3 opacity-40" />
          <p className="text-white font-medium">No players found</p>
          <p className="text-muted text-sm mt-1">Try adjusting your search or filters</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((p) => (
            <PlayerCard key={p.id} p={p} />
          ))}
        </div>
      )}
    </FadeIn>
  );
}
