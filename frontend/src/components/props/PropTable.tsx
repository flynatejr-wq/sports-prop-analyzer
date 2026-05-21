"use client";
import { useState } from "react";
import {
  TrendingUp, TrendingDown, ChevronUp, ChevronDown,
  Target, AlertTriangle, Zap, Brain, Star,
} from "lucide-react";
import { clsx } from "clsx";
import type { Prop } from "@/lib/types";
import { addPick } from "@/lib/api";
import { useNotificationStore } from "@/store";

// ── Helpers ───────────────────────────────────────────────────────────────────

const EV_COLOR = (ev: number) =>
  ev >= 10 ? "text-ev-elite" :
  ev >= 5  ? "text-ev-strong" :
  ev >= 2  ? "text-ev-good" :
  ev > 0   ? "text-primary" :
  "text-muted";

const SPORT_CHIP: Record<string, string> = {
  NBA: "bg-orange-500/20 text-orange-400",
  NFL: "bg-blue-500/20 text-blue-400",
  MLB: "bg-red-500/20 text-red-400",
  NHL: "bg-cyan-500/20 text-cyan-400",
};

type SortField = "ev" | "player" | "line" | "consensus" | "hit_rate" | "sport";
type SortDir = "asc" | "desc";

// ── Row ───────────────────────────────────────────────────────────────────────

function PropRow({ prop }: { prop: Prop }) {
  const { addToast } = useNotificationStore();
  const [adding, setAdding] = useState<"over" | "under" | null>(null);
  const [added,  setAdded]  = useState<"over" | "under" | null>(null);

  const evOver  = prop.ev_over  ?? 0;
  const evUnder = prop.ev_under ?? 0;
  const bestEv  = Math.max(evOver, evUnder);
  const bestDir = evOver >= evUnder ? "over" : "under";

  async function track(dir: "over" | "under") {
    setAdding(dir);
    try {
      await addPick({ prop_id: prop.id, direction: dir, stake: 1.0, ev_at_pick: dir === "over" ? evOver : evUnder });
      setAdded(dir);
      addToast({ type: "success", title: `${prop.player_name} ${dir.toUpperCase()} tracked` });
    } catch {
      addToast({ type: "error", title: "Failed to track pick" });
    } finally {
      setAdding(null);
    }
  }

  return (
    <tr className="border-b border-border/50 hover:bg-surface-2/50 transition-colors group">
      {/* Player */}
      <td className="px-4 py-3">
        <a href={`/props/${prop.id}`} className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary flex-shrink-0">
            {prop.player_name.charAt(0)}
          </div>
          <div className="min-w-0">
            <p className="text-white text-xs font-semibold truncate hover:text-primary transition-colors">
              {prop.player_name}
            </p>
            {prop.team && <p className="text-muted text-[10px]">{prop.team}</p>}
          </div>
        </a>
      </td>

      {/* Sport */}
      <td className="px-3 py-3">
        <span className={clsx("text-[10px] font-bold px-1.5 py-0.5 rounded", SPORT_CHIP[prop.sport] ?? "bg-surface-2 text-muted")}>
          {prop.sport}
        </span>
      </td>

      {/* Stat + Line */}
      <td className="px-3 py-3">
        <p className="text-white text-xs font-mono font-bold">{prop.line}</p>
        <p className="text-muted text-[10px]">{prop.stat_type}</p>
      </td>

      {/* Consensus */}
      <td className="px-3 py-3">
        <p className={clsx("text-xs font-mono", prop.consensus_line ? "text-white" : "text-muted")}>
          {prop.consensus_line?.toFixed(1) ?? "—"}
        </p>
        {prop.line_discrepancy != null && Math.abs(prop.line_discrepancy) > 0.1 && (
          <p className={clsx("text-[10px] font-mono", prop.line_discrepancy < 0 ? "text-success" : "text-danger")}>
            {prop.line_discrepancy > 0 ? "+" : ""}{prop.line_discrepancy.toFixed(1)}
          </p>
        )}
      </td>

      {/* EV */}
      <td className="px-3 py-3">
        <div className="flex items-center gap-1">
          {bestDir === "over"
            ? <TrendingUp size={12} className="text-success" />
            : <TrendingDown size={12} className="text-danger" />}
          <span className={clsx("text-xs font-bold font-mono", EV_COLOR(bestEv))}>
            {bestEv > 0 ? `+${bestEv.toFixed(2)}%` : `${bestEv.toFixed(2)}%`}
          </span>
        </div>
        {evOver > 0 && evUnder > 0 && (
          <p className="text-[10px] text-muted font-mono">
            O:{evOver.toFixed(1)}% U:{evUnder.toFixed(1)}%
          </p>
        )}
      </td>

      {/* Hit rate */}
      <td className="px-3 py-3">
        {prop.hit_rate_over != null ? (
          <div className="flex items-center gap-1.5">
            <div className="w-12 h-1.5 bg-surface-3 rounded-full overflow-hidden">
              <div
                className={clsx(
                  "h-full rounded-full",
                  prop.hit_rate_over >= 0.6 ? "bg-success" : prop.hit_rate_over >= 0.5 ? "bg-primary" : "bg-muted"
                )}
                style={{ width: `${Math.round(prop.hit_rate_over * 100)}%` }}
              />
            </div>
            <span className={clsx(
              "text-[10px] font-mono",
              prop.hit_rate_over >= 0.6 ? "text-success" : "text-muted"
            )}>
              {Math.round(prop.hit_rate_over * 100)}%
            </span>
          </div>
        ) : (
          <span className="text-muted text-xs">—</span>
        )}
      </td>

      {/* Flags */}
      <td className="px-3 py-3">
        <div className="flex items-center gap-1">
          {prop.is_stale   && <span title="Stale line">  <AlertTriangle size={12} className="text-warning" /></span>}
          {prop.is_boosted && <span title="Boosted">     <Zap           size={12} className="text-warning" /></span>}
          {prop.ai_insight && <span title="AI insight">  <Brain         size={12} className="text-primary" /></span>}
        </div>
      </td>

      {/* Actions */}
      <td className="px-3 py-3">
        {added ? (
          <div className="flex items-center gap-1 text-success text-[10px]">
            <Star size={10} fill="currentColor" /> Saved
          </div>
        ) : (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => track("over")}
              disabled={!!adding}
              className="px-2 py-1 bg-success/20 text-success border border-success/30 rounded text-[10px] font-semibold hover:bg-success/30 transition-colors disabled:opacity-50"
            >
              {adding === "over" ? "…" : "▲ O"}
            </button>
            <button
              onClick={() => track("under")}
              disabled={!!adding}
              className="px-2 py-1 bg-danger/20 text-danger border border-danger/30 rounded text-[10px] font-semibold hover:bg-danger/30 transition-colors disabled:opacity-50"
            >
              {adding === "under" ? "…" : "▼ U"}
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PropTable({ props }: { props: Prop[] }) {
  const [sortField, setSortField] = useState<SortField>("ev");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  }

  const sorted = [...props].sort((a, b) => {
    let aVal = 0, bVal = 0;
    if (sortField === "ev") {
      aVal = Math.max(a.ev_over ?? 0, a.ev_under ?? 0);
      bVal = Math.max(b.ev_over ?? 0, b.ev_under ?? 0);
    } else if (sortField === "line") {
      aVal = a.line; bVal = b.line;
    } else if (sortField === "consensus") {
      aVal = a.consensus_line ?? 0; bVal = b.consensus_line ?? 0;
    } else if (sortField === "hit_rate") {
      aVal = a.hit_rate_over ?? 0; bVal = b.hit_rate_over ?? 0;
    } else if (sortField === "player") {
      return sortDir === "asc"
        ? a.player_name.localeCompare(b.player_name)
        : b.player_name.localeCompare(a.player_name);
    } else if (sortField === "sport") {
      return sortDir === "asc"
        ? a.sport.localeCompare(b.sport)
        : b.sport.localeCompare(a.sport);
    }
    return sortDir === "asc" ? aVal - bVal : bVal - aVal;
  });

  function SortIcon({ field }: { field: SortField }) {
    if (sortField !== field) return <ChevronDown size={11} className="text-muted/40" />;
    return sortDir === "desc"
      ? <ChevronDown size={11} className="text-primary" />
      : <ChevronUp size={11} className="text-primary" />;
  }

  function Th({ field, label }: { field: SortField; label: string }) {
    return (
      <th
        className="px-3 py-3 text-left text-xs text-muted cursor-pointer hover:text-white transition-colors select-none"
        onClick={() => toggleSort(field)}
      >
        <div className="flex items-center gap-1">
          {label}
          <SortIcon field={field} />
        </div>
      </th>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-2/50">
              <Th field="player" label="Player" />
              <Th field="sport"  label="Sport" />
              <th className="px-3 py-3 text-left text-xs text-muted">Line</th>
              <Th field="consensus" label="Consensus" />
              <Th field="ev"        label="EV %" />
              <Th field="hit_rate"  label="Hit Rate" />
              <th className="px-3 py-3 text-left text-xs text-muted">Flags</th>
              <th className="px-3 py-3 text-left text-xs text-muted">Track</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p) => (
              <PropRow key={p.id} prop={p} />
            ))}
          </tbody>
        </table>

        {props.length === 0 && (
          <div className="text-center py-12">
            <Target size={32} className="text-muted mx-auto mb-2 opacity-40" />
            <p className="text-muted text-sm">No props to display</p>
          </div>
        )}
      </div>

      {props.length > 0 && (
        <div className="px-4 py-2 border-t border-border text-xs text-muted">
          {props.length} prop{props.length !== 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}
