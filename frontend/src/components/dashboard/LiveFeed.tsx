"use client";
import { useLiveProps } from "@/hooks/useWebSocket";
import { clsx } from "clsx";
import { Activity, Wifi, WifiOff } from "lucide-react";
import { format } from "date-fns";

export default function LiveFeed() {
  const { liveProps, connected } = useLiveProps();
  const topAlerts = liveProps
    .filter((p) => Math.max(p.ev_over ?? 0, p.ev_under ?? 0) >= 8)
    .slice(0, 5);

  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity size={15} className="text-primary" />
          <span className="text-white font-semibold text-sm">Live Feed</span>
        </div>
        <div className="flex items-center gap-1.5">
          {connected ? (
            <>
              <Wifi size={12} className="text-success" />
              <span className="text-success text-xs">Live</span>
            </>
          ) : (
            <>
              <WifiOff size={12} className="text-muted" />
              <span className="text-muted text-xs">Offline</span>
            </>
          )}
        </div>
      </div>

      {topAlerts.length === 0 ? (
        <div className="text-center py-6">
          <p className="text-muted text-xs">Scanning for high-EV props...</p>
          <div className="flex justify-center gap-1 mt-2">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {topAlerts.map((prop) => {
            const bestEv = Math.max(prop.ev_over ?? 0, prop.ev_under ?? 0);
            const direction = (prop.ev_over ?? 0) >= (prop.ev_under ?? 0) ? "OVER" : "UNDER";
            return (
              <div
                key={prop.id}
                className="flex items-center gap-2 px-3 py-2 bg-surface-2 rounded-lg border border-border hover:border-primary/30 transition-colors"
              >
                <div className={clsx(
                  "w-1.5 h-1.5 rounded-full flex-shrink-0",
                  bestEv >= 10 ? "bg-ev-elite animate-pulse" :
                  bestEv >= 5 ? "bg-ev-strong" : "bg-ev-good"
                )} />
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-medium truncate">{prop.player_name}</p>
                  <p className="text-muted text-[10px]">{prop.stat_type} {direction} {prop.line}</p>
                </div>
                <span className={clsx(
                  "text-xs font-bold font-mono flex-shrink-0",
                  bestEv >= 10 ? "text-ev-elite" :
                  bestEv >= 5 ? "text-ev-strong" : "text-ev-good"
                )}>
                  +{bestEv.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
