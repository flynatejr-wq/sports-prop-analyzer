"use client";
import { useState } from "react";
import useSWR from "swr";
import {
  Zap, TrendingUp, TrendingDown, AlertTriangle,
  BarChart2, ArrowRight, RefreshCw
} from "lucide-react";
import { clsx } from "clsx";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchSection(path: string) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) return [];
  return res.json();
}

interface SignalProp {
  id: number;
  player_name: string;
  sport: string;
  stat_type: string;
  line: number;
  ev_over?: number | null;
  ev_under?: number | null;
  edge_classification?: string | null;
  is_stale?: boolean;
  line_discrepancy?: number | null;
  consensus_line?: number | null;
  ai_insight?: string | null;
}

function SignalRow({ prop, type }: { prop: SignalProp; type: "steam" | "mispriced" | "ev" }) {
  const evOver = prop.ev_over ?? 0;
  const evUnder = prop.ev_under ?? 0;
  const bestEv = Math.max(evOver, evUnder);
  const direction = evOver >= evUnder ? "OVER" : "UNDER";

  const accent =
    type === "steam"     ? "border-l-danger text-danger"     :
    type === "mispriced" ? "border-l-warning text-warning"   :
    "border-l-ev-strong text-ev-strong";

  return (
    <div className={clsx(
      "flex items-center gap-3 px-3 py-2.5 bg-surface-2 rounded-lg border-l-2 border-r border-t border-b border-border group hover:border-primary/20 transition-colors",
      accent.split(" ")[0]
    )}>
      {type === "steam" && <Zap size={14} className="text-danger flex-shrink-0" />}
      {type === "mispriced" && <AlertTriangle size={14} className="text-warning flex-shrink-0" />}
      {type === "ev" && <BarChart2 size={14} className="text-ev-strong flex-shrink-0" />}

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <p className="text-white text-xs font-semibold truncate">{prop.player_name}</p>
          <span className="text-muted text-[10px] flex-shrink-0">{prop.sport} · {prop.stat_type}</span>
        </div>
        {prop.ai_insight && (
          <p className="text-muted text-[10px] truncate mt-0.5 group-hover:text-muted/80">
            {prop.ai_insight.slice(0, 80)}…
          </p>
        )}
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <span className="font-mono text-white text-xs">{prop.line}</span>
        {direction === "OVER"
          ? <TrendingUp size={12} className="text-success" />
          : <TrendingDown size={12} className="text-danger" />}
        <span className={clsx(
          "text-xs font-bold font-mono",
          bestEv >= 10 ? "text-ev-elite" :
          bestEv >= 5  ? "text-ev-strong" :
          bestEv >= 0  ? "text-ev-good"  : "text-muted"
        )}>
          {bestEv > 0 ? `+${bestEv.toFixed(1)}%` : `${bestEv.toFixed(1)}%`}
        </span>
      </div>
    </div>
  );
}

export default function SharpSignals() {
  const [tab, setTab] = useState<"ev" | "mispriced" | "steam">("ev");

  const { data: topEv = [], isLoading: evLoading, mutate: evMutate } = useSWR(
    "top-ev-signals",
    () => fetchSection("/api/v1/props/top?limit=6&min_ev=0"),
    { refreshInterval: 30000 }
  );

  const { data: mispriced = [], isLoading: mpLoading } = useSWR(
    "mispriced-signals",
    () => fetchSection("/api/v1/props/mispriced"),
    { refreshInterval: 60000 }
  );

  const { data: sharp = [], isLoading: sharpLoading } = useSWR(
    "sharp-signals",
    () => fetchSection("/api/v1/props/sharp-action"),
    { refreshInterval: 30000 }
  );

  const isLoading = evLoading || mpLoading || sharpLoading;

  const tabs = [
    { id: "ev"       as const, label: "Top EV",       count: topEv.length,   icon: BarChart2    },
    { id: "mispriced"as const, label: "Mispriced",    count: mispriced.length,icon: AlertTriangle},
    { id: "steam"    as const, label: "Sharp Action", count: sharp.length,   icon: Zap          },
  ];

  const current =
    tab === "ev"        ? topEv     :
    tab === "mispriced" ? mispriced :
    sharp;

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-warning" />
          <h2 className="text-white font-bold text-sm">Sharp Signals</h2>
        </div>
        <button
          onClick={() => evMutate()}
          className="p-1.5 rounded hover:bg-surface-2 transition-colors"
        >
          <RefreshCw size={12} className={clsx("text-muted", isLoading && "animate-spin")} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex px-4 gap-1 mb-3">
        {tabs.map(({ id, label, count, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              tab === id
                ? "bg-primary text-white"
                : "text-muted hover:text-white hover:bg-surface-2"
            )}
          >
            <Icon size={11} />
            {label}
            {count > 0 && (
              <span className={clsx(
                "px-1.5 py-0.5 rounded-full text-[10px] font-bold",
                tab === id ? "bg-white/20 text-white" : "bg-surface-2 text-muted"
              )}>
                {count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="px-4 pb-4 space-y-1.5">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 bg-surface-2 rounded-lg animate-pulse" />
          ))
        ) : current.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted text-sm">No signals right now</p>
            <p className="text-muted text-xs mt-1">Markets may be closed or refreshing</p>
          </div>
        ) : (
          current.slice(0, 6).map((prop: SignalProp) => (
            <SignalRow key={prop.id} prop={prop} type={tab === "mispriced" ? "mispriced" : tab === "steam" ? "steam" : "ev"} />
          ))
        )}
      </div>

      {current.length > 0 && (
        <a
          href="/props"
          className="flex items-center justify-center gap-2 py-3 border-t border-border text-muted text-xs hover:text-white transition-colors"
        >
          View all props <ArrowRight size={12} />
        </a>
      )}
    </div>
  );
}
