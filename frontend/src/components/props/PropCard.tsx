"use client";
import { useState } from "react";
import {
  TrendingUp, TrendingDown, Zap, AlertTriangle, Star,
  ChevronDown, ChevronUp, Brain, BarChart2, BookOpen,
} from "lucide-react";
import { clsx } from "clsx";
import type { Prop, EdgeClass } from "@/lib/types";
import { addPick } from "@/lib/api";

/* ── EV edge colors ─────────────────────────────────────────────────────────── */
const EDGE_COLORS: Record<EdgeClass, string> = {
  ELITE:    "text-ev-elite border-ev-elite/30 bg-ev-elite/10",
  STRONG:   "text-ev-strong border-ev-strong/30 bg-ev-strong/10",
  GOOD:     "text-ev-good border-ev-good/30 bg-ev-good/10",
  SLIGHT:   "text-ev-slight border-ev-slight/30 bg-ev-slight/10",
  MARGINAL: "text-muted border-border bg-transparent",
  NEGATIVE: "text-ev-negative border-ev-negative/30 bg-ev-negative/10",
};

const SPORT_COLORS: Record<string, string> = {
  NBA:   "bg-orange-500/20 text-orange-400",
  NFL:   "bg-blue-500/20 text-blue-400",
  MLB:   "bg-red-500/20 text-red-400",
  NHL:   "bg-cyan-500/20 text-cyan-400",
  NCAAB: "bg-yellow-500/20 text-yellow-400",
  WNBA:  "bg-purple-500/20 text-purple-400",
};

const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  prizepicks: { label: "PrizePicks", color: "bg-violet-500/20 text-violet-400 border-violet-500/20" },
  oddsapi:    { label: "Multi-Book",  color: "bg-blue-500/20 text-blue-400 border-blue-500/20" },
  underdog:   { label: "Underdog",    color: "bg-orange-500/20 text-orange-400 border-orange-500/20" },
};

/* ── Confidence from EV ─────────────────────────────────────────────────────── */
function evToConfidence(ev: number): number {
  // Map EV% to a 0–100 confidence display
  if (ev <= 0) return 35;
  if (ev >= 15) return 97;
  return Math.round(35 + (ev / 15) * 62);
}

/* ── Sub-components ─────────────────────────────────────────────────────────── */
function StatChip({
  label, value, highlight = false,
}: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="bg-surface-2 rounded-lg px-2 py-1.5 text-center">
      <p className="text-muted text-[10px]">{label}</p>
      <p className={clsx("text-sm font-semibold font-mono", highlight ? "text-success" : "text-white")}>
        {value}
      </p>
    </div>
  );
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const color =
    pct >= 85 ? "bg-ev-elite" :
    pct >= 70 ? "bg-ev-strong" :
    pct >= 55 ? "bg-ev-good" :
    "bg-muted";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-surface-2 rounded-full overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-700", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-muted text-[10px] font-mono w-8 text-right">{pct}%</span>
    </div>
  );
}

function ProbabilityBar({ over, under }: { over: number; under: number }) {
  const overPct = Math.round(over * 100);
  const underPct = Math.round(under * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] text-muted">
        <span>OVER {overPct}%</span>
        <span>UNDER {underPct}%</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden flex bg-surface-2">
        <div
          className="bg-success/70 transition-all duration-500"
          style={{ width: `${overPct}%` }}
        />
        <div className="flex-1 bg-danger/50" />
      </div>
    </div>
  );
}

function PickButton({
  label, direction, loading, done, onClick, active,
}: {
  label: string; direction: "over" | "under";
  loading: boolean; done: boolean;
  onClick: () => void; active: boolean;
}) {
  if (done) {
    return (
      <div className="flex items-center justify-center gap-1.5 py-2 rounded-lg bg-success/20 border border-success/30 text-success text-xs font-semibold">
        <Star size={12} fill="currentColor" /> Saved
      </div>
    );
  }
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={clsx(
        "py-2 rounded-lg text-xs font-semibold transition-all border",
        active
          ? direction === "over"
            ? "bg-success/20 border-success/40 text-success hover:bg-success/30"
            : "bg-danger/20 border-danger/40 text-danger hover:bg-danger/30"
          : "bg-surface-2 border-border text-muted hover:text-white hover:border-subtle",
        loading && "opacity-50",
      )}
    >
      {loading ? "..." : label}
    </button>
  );
}

/* ── Main PropCard ─────────────────────────────────────────────────────────── */
interface PropCardProps {
  prop: Prop;
  onPickAdded?: () => void;
}

export default function PropCard({ prop, onPickAdded }: PropCardProps) {
  const [pickAdding, setPickAdding] = useState<"over" | "under" | null>(null);
  const [pickAdded,  setPickAdded]  = useState<"over" | "under" | null>(null);
  const [showInsight, setShowInsight] = useState(false);

  const ev_over  = prop.ev_over  ?? 0;
  const ev_under = prop.ev_under ?? 0;
  const best_direction = ev_over >= ev_under ? "over" : "under";
  const best_ev  = Math.max(ev_over, ev_under);
  const edge     = (prop.edge_classification ?? "MARGINAL") as EdgeClass;
  const edgeStyle   = EDGE_COLORS[edge];
  const sportStyle  = SPORT_COLORS[prop.sport] ?? "bg-surface-3 text-muted";
  const sourceInfo  = SOURCE_LABELS[prop.source ?? "oddsapi"] ?? SOURCE_LABELS.oddsapi;
  const confidence  = evToConfidence(best_ev);

  const probOver  = prop.implied_prob_over  ?? 0.5;
  const probUnder = prop.implied_prob_under ?? (1 - probOver);

  async function handlePick(direction: "over" | "under") {
    setPickAdding(direction);
    try {
      await addPick({
        prop_id: prop.id,
        direction,
        stake: 1.0,
        ev_at_pick: direction === "over" ? ev_over : ev_under,
      });
      setPickAdded(direction);
      onPickAdded?.();
    } catch {
      // handle silently
    } finally {
      setPickAdding(null);
    }
  }

  return (
    <div className={clsx(
      "relative bg-surface border rounded-xl overflow-hidden transition-all duration-200",
      "hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 group",
      prop.is_boosted ? "border-warning/30" : "border-border",
    )}>
      {/* Top accent bar */}
      <div className={clsx(
        "h-0.5 w-full",
        edge === "ELITE"    ? "bg-gradient-to-r from-ev-elite via-ev-elite/60 to-transparent" :
        edge === "STRONG"   ? "bg-gradient-to-r from-ev-strong via-ev-strong/60 to-transparent" :
        edge === "GOOD"     ? "bg-gradient-to-r from-ev-good via-ev-good/60 to-transparent" :
        "bg-transparent"
      )} />

      <div className="p-4">
        {/* Boosted badge */}
        {prop.is_boosted && (
          <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-0.5 bg-warning/20 border border-warning/30 rounded-full">
            <Zap size={10} className="text-warning" />
            <span className="text-warning text-[10px] font-semibold">BOOSTED</span>
          </div>
        )}

        {/* ── Header ───────────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5 flex-1 min-w-0">
            {prop.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={prop.image_url}
                alt={prop.player_name}
                className="w-10 h-10 rounded-full object-cover bg-surface-2 flex-shrink-0 ring-2 ring-border"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/30 to-primary/10 flex-shrink-0 flex items-center justify-center text-sm font-bold text-primary ring-2 ring-border">
                {prop.player_name.charAt(0)}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="text-white font-semibold text-sm truncate">{prop.player_name}</p>
              <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                <span className={clsx("text-[10px] font-bold px-1.5 py-0.5 rounded", sportStyle)}>
                  {prop.sport}
                </span>
                <span className={clsx(
                  "text-[10px] px-1.5 py-0.5 rounded border",
                  sourceInfo.color
                )}>
                  {sourceInfo.label}
                </span>
                {prop.team && <span className="text-muted text-[10px]">{prop.team}</span>}
                {prop.opponent && <span className="text-muted text-[10px]">vs {prop.opponent}</span>}
              </div>
            </div>
          </div>

          {/* EV Badge */}
          <div className={clsx(
            "flex-shrink-0 px-2.5 py-1.5 rounded-lg border text-xs font-bold font-mono",
            edgeStyle
          )}>
            {best_ev > 0 ? `+${best_ev.toFixed(1)}%` : `${best_ev.toFixed(1)}%`}
          </div>
        </div>

        {/* ── Confidence ───────────────────────────────────────────────────── */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-0.5">
            <span className="text-muted text-[10px] flex items-center gap-1">
              <Brain size={9} /> AI Confidence
            </span>
            <span className={clsx(
              "text-[10px] font-bold uppercase",
              confidence >= 85 ? "text-ev-elite" :
              confidence >= 70 ? "text-ev-strong" :
              confidence >= 55 ? "text-ev-good" :
              "text-muted"
            )}>
              {edge}
            </span>
          </div>
          <ConfidenceMeter value={confidence} />
        </div>

        {/* ── Line ─────────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mb-3 py-3 border-y border-border">
          <div className="text-center">
            <p className="text-muted text-[10px] mb-1">Line</p>
            <p className="text-white text-2xl font-bold font-mono">{prop.line}</p>
            <p className="text-muted text-[10px] mt-0.5 truncate max-w-[80px]">{prop.stat_type}</p>
          </div>

          <div className="flex flex-col items-center gap-1.5">
            <button
              onClick={() => handlePick("over")}
              disabled={!!pickAdding || pickAdded === "over"}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border min-w-[90px] justify-center",
                best_direction === "over"
                  ? "bg-success/20 text-success border-success/30 hover:bg-success/30"
                  : "bg-surface-2 text-muted border-border hover:border-subtle hover:text-white",
                pickAdded === "over" && "opacity-60 cursor-default",
              )}
            >
              <TrendingUp size={12} />
              OVER {ev_over > 0 ? `+${ev_over.toFixed(1)}%` : ""}
            </button>
            <button
              onClick={() => handlePick("under")}
              disabled={!!pickAdding || pickAdded === "under"}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border min-w-[90px] justify-center",
                best_direction === "under"
                  ? "bg-danger/20 text-danger border-danger/30 hover:bg-danger/30"
                  : "bg-surface-2 text-muted border-border hover:border-subtle hover:text-white",
                pickAdded === "under" && "opacity-60 cursor-default",
              )}
            >
              <TrendingDown size={12} />
              UNDER {ev_under > 0 ? `+${ev_under.toFixed(1)}%` : ""}
            </button>
          </div>

          <div className="text-center">
            <p className="text-muted text-[10px] mb-1">Consensus</p>
            <p className={clsx(
              "text-lg font-bold font-mono",
              prop.consensus_line ? "text-white" : "text-muted"
            )}>
              {prop.consensus_line?.toFixed(1) ?? "N/A"}
            </p>
            {prop.line_discrepancy != null && Math.abs(prop.line_discrepancy) > 0.1 && (
              <p className={clsx(
                "text-xs font-mono",
                prop.line_discrepancy < 0 ? "text-success" : "text-danger"
              )}>
                {prop.line_discrepancy > 0 ? "+" : ""}{prop.line_discrepancy.toFixed(1)}
              </p>
            )}
          </div>
        </div>

        {/* ── Probability bar ───────────────────────────────────────────────── */}
        <div className="mb-3">
          <ProbabilityBar over={probOver} under={probUnder} />
        </div>

        {/* ── Stats row ────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          <StatChip label="Season" value={prop.season_avg?.toFixed(1) ?? "—"} />
          <StatChip label="L5 Avg"  value={prop.last_5_avg?.toFixed(1)  ?? "—"} />
          <StatChip
            label="Hit Rate"
            value={prop.hit_rate_over != null ? `${(prop.hit_rate_over * 100).toFixed(0)}%` : "—"}
            highlight={prop.hit_rate_over != null && prop.hit_rate_over > 0.6}
          />
        </div>

        {/* ── Flags ────────────────────────────────────────────────────────── */}
        {(prop.is_stale || prop.ml_risk_level) && (
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            {prop.is_stale && (
              <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-warning/10 border border-warning/20 rounded-full text-warning">
                <AlertTriangle size={9} /> Stale Line
              </span>
            )}
            {prop.ml_risk_level && (
              <span className={clsx(
                "text-[10px] px-2 py-0.5 rounded-full border",
                prop.ml_risk_level === "LOW"    ? "bg-success/10 border-success/20 text-success" :
                prop.ml_risk_level === "MEDIUM" ? "bg-warning/10 border-warning/20 text-warning" :
                "bg-danger/10 border-danger/20 text-danger"
              )}>
                {prop.ml_risk_level} RISK
              </span>
            )}
            {prop.ml_confidence != null && (
              <span className="text-[10px] px-2 py-0.5 bg-primary/10 border border-primary/20 rounded-full text-primary">
                {prop.ml_confidence.toFixed(0)}% ML conf.
              </span>
            )}
          </div>
        )}

        {/* ── AI Insight toggle ─────────────────────────────────────────────── */}
        {prop.ai_insight && (
          <div className="mb-3">
            <button
              onClick={() => setShowInsight(!showInsight)}
              className="w-full flex items-center justify-between px-3 py-2 bg-primary/5 border border-primary/15 rounded-lg hover:bg-primary/10 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Brain size={12} className="text-primary" />
                <span className="text-primary text-xs font-medium">Why AI likes this</span>
              </div>
              {showInsight
                ? <ChevronUp size={13} className="text-muted" />
                : <ChevronDown size={13} className="text-muted" />}
            </button>
            {showInsight && (
              <div className="mt-2 px-3 py-2.5 bg-surface-2 border border-border rounded-lg">
                <p className="text-muted text-xs leading-relaxed">{prop.ai_insight}</p>
              </div>
            )}
          </div>
        )}

        {/* ── Stat details toggle ───────────────────────────────────────────── */}
        {(prop.home_avg != null || prop.away_avg != null || prop.ml_projection != null) && (
          <div className="mt-2 pt-2 border-t border-border">
            <div className="grid grid-cols-3 gap-2">
              {prop.home_avg != null && (
                <StatChip label="Home" value={prop.home_avg.toFixed(1)} />
              )}
              {prop.away_avg != null && (
                <StatChip label="Away" value={prop.away_avg.toFixed(1)} />
              )}
              {prop.ml_projection != null && (
                <StatChip label="ML Proj." value={prop.ml_projection.toFixed(1)} highlight />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
