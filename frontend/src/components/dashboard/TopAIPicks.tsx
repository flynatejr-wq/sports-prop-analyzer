"use client";
import useSWR from "swr";
import { TrendingUp, TrendingDown, Brain, ArrowRight } from "lucide-react";
import { clsx } from "clsx";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchTop5() {
  const res = await fetch(`${BASE}/api/v1/props/top?limit=5&min_ev=0`);
  if (!res.ok) return [];
  return res.json();
}

interface Pick {
  id: number;
  player_name: string;
  sport: string;
  stat_type: string;
  line: number;
  ev_over?: number | null;
  ev_under?: number | null;
  edge_classification?: string | null;
  consensus_line?: number | null;
  implied_prob_over?: number | null;
  ai_insight?: string | null;
}

const EDGE_BG: Record<string, string> = {
  ELITE:    "from-ev-elite/20 to-ev-elite/5  border-ev-elite/25",
  STRONG:   "from-ev-strong/20 to-ev-strong/5  border-ev-strong/25",
  GOOD:     "from-ev-good/20 to-ev-good/5  border-ev-good/25",
  SLIGHT:   "from-primary/10 to-transparent border-primary/15",
  MARGINAL: "from-surface-2 to-surface border-border",
  NEGATIVE: "from-surface-2 to-surface border-border",
};

const EDGE_TEXT: Record<string, string> = {
  ELITE:    "text-ev-elite",
  STRONG:   "text-ev-strong",
  GOOD:     "text-ev-good",
  SLIGHT:   "text-primary",
  MARGINAL: "text-muted",
  NEGATIVE: "text-muted",
};

export default function TopAIPicks() {
  const { data: picks = [], isLoading } = useSWR(
    "top-ai-picks",
    fetchTop5,
    { refreshInterval: 30000 }
  );

  if (!isLoading && picks.length === 0) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-primary" />
          <h2 className="text-white font-bold text-sm">Today&apos;s Top AI Picks</h2>
          <span className="text-muted text-xs">— Best edge right now</span>
        </div>
        <a
          href="/props"
          className="flex items-center gap-1 text-muted text-xs hover:text-white transition-colors"
        >
          All props <ArrowRight size={11} />
        </a>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-28 bg-surface border border-border rounded-xl animate-pulse" />
            ))
          : picks.slice(0, 5).map((pick: Pick, i: number) => {
              const evOver = pick.ev_over ?? 0;
              const evUnder = pick.ev_under ?? 0;
              const bestEv = Math.max(evOver, evUnder);
              const direction = evOver >= evUnder ? "OVER" : "UNDER";
              const edge = pick.edge_classification ?? "MARGINAL";
              const bg = EDGE_BG[edge] ?? EDGE_BG.MARGINAL;
              const evText = EDGE_TEXT[edge] ?? "text-muted";

              return (
                <a
                  key={pick.id}
                  href="/props"
                  className={clsx(
                    "relative flex flex-col gap-2 p-3 rounded-xl border bg-gradient-to-br",
                    "hover:scale-[1.02] transition-transform duration-200 cursor-pointer",
                    bg
                  )}
                >
                  {/* Rank badge */}
                  <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-black/30 flex items-center justify-center">
                    <span className="text-[10px] text-white font-bold">#{i + 1}</span>
                  </div>

                  {/* Player */}
                  <div>
                    <p className="text-white text-xs font-bold truncate pr-6">{pick.player_name}</p>
                    <p className="text-muted text-[10px]">{pick.sport} · {pick.stat_type}</p>
                  </div>

                  {/* Line + direction */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-white font-mono font-bold text-lg">{pick.line}</span>
                    <div className={clsx(
                      "flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold",
                      direction === "OVER"
                        ? "bg-success/20 text-success"
                        : "bg-danger/20 text-danger"
                    )}>
                      {direction === "OVER"
                        ? <TrendingUp size={9} />
                        : <TrendingDown size={9} />}
                      {direction}
                    </div>
                  </div>

                  {/* EV */}
                  <div className={clsx("text-xs font-bold font-mono", evText)}>
                    {bestEv > 0 ? `+${bestEv.toFixed(2)}%` : `${bestEv.toFixed(2)}%`} EV
                  </div>
                </a>
              );
            })}
      </div>
    </div>
  );
}
