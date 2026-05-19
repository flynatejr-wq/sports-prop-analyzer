"use client";
import { useState } from "react";
import { TrendingUp, TrendingDown, Zap, AlertTriangle, Star } from "lucide-react";
import { clsx } from "clsx";
import type { Prop, EdgeClass } from "@/lib/types";
import { addPick } from "@/lib/api";

const EDGE_COLORS: Record<EdgeClass, string> = {
  ELITE: "text-ev-elite border-ev-elite/30 bg-ev-elite/10",
  STRONG: "text-ev-strong border-ev-strong/30 bg-ev-strong/10",
  GOOD: "text-ev-good border-ev-good/30 bg-ev-good/10",
  SLIGHT: "text-ev-slight border-ev-slight/30 bg-ev-slight/10",
  MARGINAL: "text-muted border-border bg-transparent",
  NEGATIVE: "text-ev-negative border-ev-negative/30 bg-ev-negative/10",
};

const SPORT_COLORS: Record<string, string> = {
  NBA: "bg-orange-500/20 text-orange-400",
  NFL: "bg-blue-500/20 text-blue-400",
  MLB: "bg-red-500/20 text-red-400",
  NHL: "bg-cyan-500/20 text-cyan-400",
  NCAAB: "bg-yellow-500/20 text-yellow-400",
  WNBA: "bg-purple-500/20 text-purple-400",
};

interface PropCardProps {
  prop: Prop;
  onPickAdded?: () => void;
}

export default function PropCard({ prop, onPickAdded }: PropCardProps) {
  const [pickAdding, setPickAdding] = useState<"over" | "under" | null>(null);
  const [pickAdded, setPickAdded] = useState<"over" | "under" | null>(null);

  const ev_over = prop.ev_over ?? 0;
  const ev_under = prop.ev_under ?? 0;
  const best_direction = ev_over >= ev_under ? "over" : "under";
  const best_ev = Math.max(ev_over, ev_under);
  const edge = (prop.edge_classification ?? "MARGINAL") as EdgeClass;
  const edgeStyle = EDGE_COLORS[edge];
  const sportStyle = SPORT_COLORS[prop.sport] ?? "bg-surface-3 text-muted";

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
      // handle silently — user can retry
    } finally {
      setPickAdding(null);
    }
  }

  return (
    <div className={clsx(
      "relative bg-surface border rounded-xl p-4 transition-all duration-200 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 group",
      prop.is_boosted ? "border-warning/30" : "border-border"
    )}>
      {/* Boosted badge */}
      {prop.is_boosted && (
        <div className="absolute -top-2 left-4 flex items-center gap-1 px-2 py-0.5 bg-warning/20 border border-warning/30 rounded-full">
          <Zap size={10} className="text-warning" />
          <span className="text-warning text-[10px] font-semibold">BOOSTED</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5 flex-1 min-w-0">
          {prop.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={prop.image_url}
              alt={prop.player_name}
              className="w-9 h-9 rounded-full object-cover bg-surface-2 flex-shrink-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-surface-2 flex-shrink-0 flex items-center justify-center text-sm font-bold text-white">
              {prop.player_name.charAt(0)}
            </div>
          )}
          <div className="min-w-0">
            <p className="text-white font-semibold text-sm truncate">{prop.player_name}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={clsx("text-[10px] font-bold px-1.5 py-0.5 rounded", sportStyle)}>
                {prop.sport}
              </span>
              {prop.team && <span className="text-muted text-[10px]">{prop.team}</span>}
              {prop.opponent && <span className="text-muted text-[10px]">vs {prop.opponent}</span>}
            </div>
          </div>
        </div>

        {/* EV Badge */}
        <div className={clsx("flex-shrink-0 px-2.5 py-1 rounded-lg border text-xs font-bold", edgeStyle)}>
          +{best_ev.toFixed(1)}%
        </div>
      </div>

      {/* Stat line */}
      <div className="flex items-center justify-between mb-3 py-3 border-y border-border">
        <div className="text-center">
          <p className="text-muted text-xs mb-1">PP Line</p>
          <p className="text-white text-2xl font-bold font-mono">{prop.line}</p>
          <p className="text-muted text-xs mt-0.5">{prop.stat_type}</p>
        </div>
        <div className="flex flex-col items-center gap-1">
          <div className={clsx(
            "flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold",
            best_direction === "over" ? "bg-success/20 text-success border border-success/30" : "bg-surface-2 text-muted"
          )}>
            <TrendingUp size={12} />
            OVER {ev_over > 0 ? `+${ev_over.toFixed(1)}%` : ""}
          </div>
          <div className={clsx(
            "flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold",
            best_direction === "under" ? "bg-danger/20 text-danger border border-danger/30" : "bg-surface-2 text-muted"
          )}>
            <TrendingDown size={12} />
            UNDER {ev_under > 0 ? `+${ev_under.toFixed(1)}%` : ""}
          </div>
        </div>
        <div className="text-center">
          <p className="text-muted text-xs mb-1">Consensus</p>
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

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <StatChip label="Season" value={prop.season_avg?.toFixed(1) ?? "—"} />
        <StatChip label="L5 Avg" value={prop.last_5_avg?.toFixed(1) ?? "—"} />
        <StatChip
          label="Hit Rate"
          value={prop.hit_rate_over != null ? `${(prop.hit_rate_over * 100).toFixed(0)}%` : "—"}
          highlight={prop.hit_rate_over != null && prop.hit_rate_over > 0.6}
        />
      </div>

      {/* Flags row */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {prop.is_stale && (
          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-warning/10 border border-warning/20 rounded-full text-warning">
            <AlertTriangle size={9} /> Stale Line
          </span>
        )}
        {prop.ml_risk_level && (
          <span className={clsx(
            "text-[10px] px-2 py-0.5 rounded-full border",
            prop.ml_risk_level === "LOW" ? "bg-success/10 border-success/20 text-success" :
            prop.ml_risk_level === "MEDIUM" ? "bg-warning/10 border-warning/20 text-warning" :
            "bg-danger/10 border-danger/20 text-danger"
          )}>
            {prop.ml_risk_level} RISK
          </span>
        )}
        {prop.ml_confidence != null && (
          <span className="text-[10px] px-2 py-0.5 bg-primary/10 border border-primary/20 rounded-full text-primary">
            {prop.ml_confidence.toFixed(0)}% conf.
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-2 gap-2">
        <PickButton
          label="Pick Over"
          direction="over"
          loading={pickAdding === "over"}
          done={pickAdded === "over"}
          onClick={() => handlePick("over")}
          active={best_direction === "over"}
        />
        <PickButton
          label="Pick Under"
          direction="under"
          loading={pickAdding === "under"}
          done={pickAdded === "under"}
          onClick={() => handlePick("under")}
          active={best_direction === "under"}
        />
      </div>
    </div>
  );
}

function StatChip({ label, value, highlight = false }: {
  label: string; value: string; highlight?: boolean;
}) {
  return (
    <div className="bg-surface-2 rounded-lg px-2 py-1.5 text-center">
      <p className="text-muted text-[10px]">{label}</p>
      <p className={clsx("text-sm font-semibold font-mono", highlight ? "text-success" : "text-white")}>
        {value}
      </p>
    </div>
  );
}

function PickButton({
  label, direction, loading, done, onClick, active
}: {
  label: string;
  direction: "over" | "under";
  loading: boolean;
  done: boolean;
  onClick: () => void;
  active: boolean;
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
        loading && "opacity-50"
      )}
    >
      {loading ? "..." : label}
    </button>
  );
}
