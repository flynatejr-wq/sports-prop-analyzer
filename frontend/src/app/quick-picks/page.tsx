"use client";
import { useState, useCallback } from "react";
import useSWR from "swr";
import { motion, AnimatePresence, PanInfo } from "framer-motion";
import {
  TrendingUp, TrendingDown, Brain, CheckCircle, XCircle,
  ChevronUp, ChevronDown, Zap, RefreshCw, Star,
} from "lucide-react";
import { clsx } from "clsx";
import { addPick } from "@/lib/api";
import { useNotificationStore } from "@/store";
import type { Prop } from "@/lib/types";

// ── Fetch ─────────────────────────────────────────────────────────────────────

async function fetchQuickPicks(): Promise<Prop[]> {
  const res = await fetch("/api/v1/props/top?limit=20&min_ev=0");
  if (!res.ok) return [];
  return res.json();
}

// ── Edge gradient configs ─────────────────────────────────────────────────────

const EDGE_GRADIENTS: Record<string, string> = {
  ELITE:    "from-ev-elite/30 via-surface to-surface",
  STRONG:   "from-ev-strong/25 via-surface to-surface",
  GOOD:     "from-ev-good/20 via-surface to-surface",
  SLIGHT:   "from-primary/15 via-surface to-surface",
  MARGINAL: "from-surface-2 via-surface to-surface",
  NEGATIVE: "from-danger/10 via-surface to-surface",
};

const EV_COLOR: Record<string, string> = {
  ELITE:    "text-ev-elite",
  STRONG:   "text-ev-strong",
  GOOD:     "text-ev-good",
  SLIGHT:   "text-primary",
  MARGINAL: "text-muted",
  NEGATIVE: "text-danger",
};

// ── Quick pick card ───────────────────────────────────────────────────────────

interface QuickCardProps {
  prop: Prop;
  onSwipeUp: () => void;
  onSwipeDown: () => void;
  onTrackOver: () => void;
  onTrackUnder: () => void;
  isActive: boolean;
}

function QuickCard({ prop, onSwipeUp, onSwipeDown, onTrackOver, onTrackUnder, isActive }: QuickCardProps) {
  const evOver  = prop.ev_over  ?? 0;
  const evUnder = prop.ev_under ?? 0;
  const bestEv  = Math.max(evOver, evUnder);
  const bestDir = evOver >= evUnder ? "OVER" : "UNDER";
  const edge    = prop.edge_classification ?? "MARGINAL";

  function handleDragEnd(_: unknown, info: PanInfo) {
    if (info.offset.y < -80) onSwipeUp();
    else if (info.offset.y > 80) onSwipeDown();
  }

  return (
    <motion.div
      drag={isActive ? "y" : false}
      dragConstraints={{ top: 0, bottom: 0 }}
      dragElastic={0.3}
      onDragEnd={handleDragEnd}
      className={clsx(
        "absolute inset-0 cursor-grab active:cursor-grabbing select-none",
        "bg-gradient-to-b rounded-2xl border overflow-hidden",
        EDGE_GRADIENTS[edge] ?? EDGE_GRADIENTS.MARGINAL,
        edge === "ELITE"  ? "border-ev-elite/30" :
        edge === "STRONG" ? "border-ev-strong/30" :
        edge === "GOOD"   ? "border-ev-good/30" :
        "border-border"
      )}
    >
      {/* Top accent line */}
      <div className={clsx(
        "h-1",
        edge === "ELITE"  ? "bg-gradient-to-r from-ev-elite to-transparent" :
        edge === "STRONG" ? "bg-gradient-to-r from-ev-strong to-transparent" :
        edge === "GOOD"   ? "bg-gradient-to-r from-ev-good to-transparent" :
        "bg-transparent"
      )} />

      <div className="h-full flex flex-col p-6 gap-4 pb-24">
        {/* Player header */}
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/40 to-primary/10 flex items-center justify-center text-2xl font-bold text-primary ring-2 ring-border flex-shrink-0">
            {prop.player_name.charAt(0)}
          </div>
          <div>
            <h2 className="text-white text-xl font-bold">{prop.player_name}</h2>
            <p className="text-muted text-sm">{prop.sport} · {prop.team ?? "—"}</p>
          </div>
          <div className={clsx(
            "ml-auto px-3 py-1.5 rounded-xl border text-center",
            edge === "ELITE"  ? "bg-ev-elite/10 border-ev-elite/30"  :
            edge === "STRONG" ? "bg-ev-strong/10 border-ev-strong/30" :
            edge === "GOOD"   ? "bg-ev-good/10 border-ev-good/30"    :
            "bg-surface-2 border-border"
          )}>
            <p className={clsx("text-2xl font-bold font-mono", EV_COLOR[edge])}>
              {bestEv > 0 ? `+${bestEv.toFixed(1)}%` : `${bestEv.toFixed(1)}%`}
            </p>
            <p className="text-muted text-[10px] font-medium">{edge}</p>
          </div>
        </div>

        {/* Main stat display */}
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <p className="text-muted text-sm uppercase tracking-wider">{prop.stat_type}</p>
          <p className="text-white text-7xl font-black font-mono leading-none">{prop.line}</p>
          <div className={clsx(
            "flex items-center gap-2 px-5 py-2.5 rounded-xl text-xl font-bold",
            bestDir === "OVER"
              ? "bg-success/20 text-success border border-success/30"
              : "bg-danger/20 text-danger border border-danger/30"
          )}>
            {bestDir === "OVER"
              ? <TrendingUp size={20} />
              : <TrendingDown size={20} />}
            {bestDir}
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-surface-2 rounded-xl p-3 text-center">
            <p className="text-muted text-[10px]">Season</p>
            <p className="text-white font-bold">{prop.season_avg?.toFixed(1) ?? "—"}</p>
          </div>
          <div className="bg-surface-2 rounded-xl p-3 text-center">
            <p className="text-muted text-[10px]">L5 Avg</p>
            <p className="text-white font-bold">{prop.last_5_avg?.toFixed(1) ?? "—"}</p>
          </div>
          <div className="bg-surface-2 rounded-xl p-3 text-center">
            <p className="text-muted text-[10px]">Hit Rate</p>
            <p className={clsx(
              "font-bold",
              prop.hit_rate_over != null && prop.hit_rate_over >= 0.6 ? "text-success" : "text-white"
            )}>
              {prop.hit_rate_over != null ? `${(prop.hit_rate_over * 100).toFixed(0)}%` : "—"}
            </p>
          </div>
        </div>

        {/* AI insight */}
        {prop.ai_insight && (
          <div className="flex items-start gap-2 px-3 py-2.5 bg-primary/5 border border-primary/15 rounded-xl">
            <Brain size={14} className="text-primary mt-0.5 flex-shrink-0" />
            <p className="text-muted text-xs leading-relaxed line-clamp-2">{prop.ai_insight}</p>
          </div>
        )}

        {/* Flags */}
        <div className="flex items-center gap-2">
          {prop.is_stale && (
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-warning/10 border border-warning/20 rounded-full text-warning">
              Stale Line
            </span>
          )}
          {prop.is_boosted && (
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-warning/10 border border-warning/20 rounded-full text-warning">
              <Zap size={9} /> Boosted
            </span>
          )}
          {prop.consensus_line && (
            <span className="text-muted text-[10px] ml-auto">
              Consensus: {prop.consensus_line.toFixed(1)}
            </span>
          )}
        </div>
      </div>

      {/* Action buttons — pinned to bottom */}
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-surface via-surface/95 to-transparent">
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={(e) => { e.stopPropagation(); onTrackOver(); }}
            className="flex items-center justify-center gap-2 py-3 rounded-xl bg-success/20 border border-success/40 text-success font-bold text-sm hover:bg-success/30 active:scale-95 transition-all"
          >
            <TrendingUp size={16} />
            OVER {evOver > 0 ? `+${evOver.toFixed(1)}%` : ""}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onTrackUnder(); }}
            className="flex items-center justify-center gap-2 py-3 rounded-xl bg-danger/20 border border-danger/40 text-danger font-bold text-sm hover:bg-danger/30 active:scale-95 transition-all"
          >
            <TrendingDown size={16} />
            UNDER {evUnder > 0 ? `+${evUnder.toFixed(1)}%` : ""}
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function QuickPicksPage() {
  const { addToast } = useNotificationStore();
  const { data: props = [], isLoading, mutate } = useSWR("quick-picks", fetchQuickPicks, {
    refreshInterval: 60000,
  });

  const [index, setIndex] = useState(0);
  const [saved, setSaved] = useState<Set<number>>(new Set());
  const [direction, setDirection] = useState<"up" | "down" | null>(null);

  const total = props.length;
  const current = props[index];
  const next    = props[index + 1];

  const goNext = useCallback((dir: "up" | "down") => {
    setDirection(dir);
    setTimeout(() => {
      setIndex((i) => Math.min(i + 1, total - 1));
      setDirection(null);
    }, 200);
  }, [total]);

  const goPrev = useCallback(() => {
    setIndex((i) => Math.max(i - 1, 0));
  }, []);

  async function track(prop: Prop, dir: "over" | "under") {
    const ev = dir === "over" ? (prop.ev_over ?? 0) : (prop.ev_under ?? 0);
    try {
      await addPick({ prop_id: prop.id, direction: dir, stake: 1.0, ev_at_pick: ev });
      setSaved((s) => new Set(s).add(prop.id));
      addToast({ type: "success", title: `${prop.player_name} ${dir.toUpperCase()} tracked!` });
      goNext("up");
    } catch {
      addToast({ type: "error", title: "Failed to save pick" });
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted">Loading props...</p>
        </div>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
        <div className="text-center">
          <p className="text-white font-medium text-lg mb-2">No props available</p>
          <button onClick={() => mutate()} className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
            Refresh
          </button>
        </div>
      </div>
    );
  }

  if (index >= total) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-success/20 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle size={32} className="text-success" />
          </div>
          <p className="text-white font-bold text-xl">All props reviewed!</p>
          <p className="text-muted text-sm">{saved.size} picks tracked</p>
          <button
            onClick={() => { setIndex(0); setSaved(new Set()); mutate(); }}
            className="flex items-center gap-2 px-6 py-2.5 bg-primary text-white rounded-xl font-semibold hover:bg-primary-hover transition-colors mx-auto"
          >
            <RefreshCw size={16} /> Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-md mx-auto relative">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 flex-shrink-0">
        <div>
          <h1 className="text-white font-bold text-lg">Quick Picks</h1>
          <p className="text-muted text-xs">Swipe up to skip · Tap to track</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted text-sm">{index + 1}/{total}</span>
          {saved.size > 0 && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-success/20 rounded-full text-success text-xs font-semibold">
              <Star size={10} fill="currentColor" /> {saved.size}
            </span>
          )}
          <button onClick={() => mutate()} className="p-1.5 rounded-lg hover:bg-surface-2 transition-colors">
            <RefreshCw size={14} className="text-muted" />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-surface-2 mx-4 rounded-full overflow-hidden flex-shrink-0">
        <div
          className="h-full bg-primary rounded-full transition-all duration-300"
          style={{ width: `${((index + 1) / total) * 100}%` }}
        />
      </div>

      {/* Card stack */}
      <div className="flex-1 relative mx-4 my-4 min-h-0">
        {/* Ghost card behind (next) */}
        {next && (
          <div className="absolute inset-0 scale-95 opacity-50 rounded-2xl bg-surface border border-border translate-y-3 z-0" />
        )}

        {/* Active card */}
        <AnimatePresence mode="wait">
          {current && (
            <motion.div
              key={current.id}
              className="absolute inset-0 z-10"
              initial={{ opacity: 0, y: direction === "up" ? 50 : -50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{
                opacity: 0,
                y: direction === "up" ? -100 : 100,
                transition: { duration: 0.2 }
              }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            >
              <QuickCard
                prop={current}
                isActive={true}
                onSwipeUp={() => goNext("up")}
                onSwipeDown={goPrev}
                onTrackOver={() => track(current, "over")}
                onTrackUnder={() => track(current, "under")}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav hints */}
      <div className="flex items-center justify-between px-6 py-3 flex-shrink-0">
        <button
          onClick={goPrev}
          disabled={index === 0}
          className="flex items-center gap-1.5 text-muted text-xs disabled:opacity-30 hover:text-white transition-colors"
        >
          <ChevronDown size={14} /> Previous
        </button>
        <button
          onClick={() => goNext("up")}
          disabled={index >= total - 1}
          className="flex items-center gap-1.5 text-muted text-xs disabled:opacity-30 hover:text-white transition-colors"
        >
          Skip <ChevronUp size={14} />
        </button>
      </div>
    </div>
  );
}
