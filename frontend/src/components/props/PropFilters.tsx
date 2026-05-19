"use client";
import { clsx } from "clsx";
import type { FilterState, Sport } from "@/lib/types";

const SPORTS: Array<Sport | "ALL"> = ["ALL", "NBA", "NFL", "MLB", "NHL", "NCAAB"];
const STAT_TYPES = [
  "All", "Points", "Rebounds", "Assists", "3-Pointers Made",
  "Passing Yards", "Rushing Yards", "Receiving Yards",
  "Hits", "Pitcher Strikeouts", "Shots on Goal",
];

interface PropFiltersProps {
  filters: FilterState;
  onChange: (f: FilterState) => void;
}

export default function PropFilters({ filters, onChange }: PropFiltersProps) {
  function set<K extends keyof FilterState>(key: K, val: FilterState[K]) {
    onChange({ ...filters, [key]: val });
  }

  return (
    <div className="flex flex-wrap items-center gap-3 py-3">
      {/* Sport tabs */}
      <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg">
        {SPORTS.map((s) => (
          <button
            key={s}
            onClick={() => set("sport", s)}
            className={clsx(
              "px-3 py-1.5 rounded-md text-xs font-semibold transition-all",
              filters.sport === s
                ? "bg-primary text-white shadow-sm"
                : "text-muted hover:text-white"
            )}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Stat type */}
      <select
        value={filters.stat_type || "All"}
        onChange={(e) => set("stat_type", e.target.value === "All" ? "" : e.target.value)}
        className="px-3 py-1.5 bg-surface-2 border border-border rounded-lg text-xs text-white focus:outline-none focus:border-primary"
      >
        {STAT_TYPES.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>

      {/* Min EV */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted">Min EV:</span>
        <div className="flex items-center gap-1 bg-surface-2 rounded-lg p-1">
          {[0, 2, 5, 10].map((v) => (
            <button
              key={v}
              onClick={() => set("min_ev", v)}
              className={clsx(
                "px-2.5 py-1 rounded text-xs font-medium transition-all",
                filters.min_ev === v
                  ? "bg-primary text-white"
                  : "text-muted hover:text-white"
              )}
            >
              {v === 0 ? "All" : `>${v}%`}
            </button>
          ))}
        </div>
      </div>

      {/* Toggles */}
      <label className="flex items-center gap-2 cursor-pointer">
        <div
          onClick={() => set("show_stale", !filters.show_stale)}
          className={clsx(
            "w-8 h-4 rounded-full transition-colors relative",
            filters.show_stale ? "bg-warning" : "bg-surface-3"
          )}
        >
          <div className={clsx(
            "absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform",
            filters.show_stale ? "translate-x-4" : "translate-x-0.5"
          )} />
        </div>
        <span className="text-xs text-muted">Stale Lines</span>
      </label>

      <label className="flex items-center gap-2 cursor-pointer">
        <div
          onClick={() => set("show_boosted", !filters.show_boosted)}
          className={clsx(
            "w-8 h-4 rounded-full transition-colors relative",
            filters.show_boosted ? "bg-warning" : "bg-surface-3"
          )}
        >
          <div className={clsx(
            "absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform",
            filters.show_boosted ? "translate-x-4" : "translate-x-0.5"
          )} />
        </div>
        <span className="text-xs text-muted">Boosted Only</span>
      </label>
    </div>
  );
}
