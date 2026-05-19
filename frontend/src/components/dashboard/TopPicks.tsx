"use client";
import { useState } from "react";
import PropCard from "@/components/props/PropCard";
import { useBestBets } from "@/hooks/useProps";
import { Flame, RefreshCw } from "lucide-react";
import { clsx } from "clsx";

const SPORTS = ["ALL", "NBA", "NFL", "MLB", "NHL"];

export default function TopPicks() {
  const [activeSport, setActiveSport] = useState("ALL");
  const { data: props = [], isLoading, mutate } = useBestBets(
    activeSport !== "ALL" ? activeSport : undefined
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Flame size={18} className="text-warning" />
          <h2 className="text-white font-bold text-base">Best Bets</h2>
          {!isLoading && (
            <span className="px-2 py-0.5 bg-surface-2 border border-border rounded-full text-muted text-xs">
              {props.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Sport filter chips */}
          <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg">
            {SPORTS.map((s) => (
              <button
                key={s}
                onClick={() => setActiveSport(s)}
                className={clsx(
                  "px-2.5 py-1 rounded text-xs font-medium transition-all",
                  activeSport === s ? "bg-primary text-white" : "text-muted hover:text-white"
                )}
              >
                {s}
              </button>
            ))}
          </div>
          <button
            onClick={() => mutate()}
            className="p-1.5 rounded-lg hover:bg-surface-2 transition-colors"
          >
            <RefreshCw size={13} className={clsx("text-muted", isLoading && "animate-spin")} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-72 bg-surface border border-border rounded-xl animate-pulse" />
          ))}
        </div>
      ) : props.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Flame size={32} className="text-muted mb-3 opacity-50" />
          <p className="text-white font-medium">No high-EV props right now</p>
          <p className="text-muted text-sm mt-1">Check back when markets open</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {props.slice(0, 9).map((prop) => (
            <PropCard key={prop.id} prop={prop} onPickAdded={() => mutate()} />
          ))}
        </div>
      )}
    </div>
  );
}
