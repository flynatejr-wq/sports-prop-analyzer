"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Wifi, WifiOff, Activity, Flame, Clock, RefreshCw } from "lucide-react";
import { clsx } from "clsx";
import { format } from "date-fns";
import PropCard from "@/components/props/PropCard";
import { useLiveProps } from "@/hooks/useWebSocket";
import { FadeIn, StaggerChildren, StaggerItem, CountUp } from "@/components/ui/AnimatedCard";
import type { Prop } from "@/lib/types";

export default function LivePropsPage() {
  const { liveProps, connected } = useLiveProps();
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [filter, setFilter] = useState<"all" | "high" | "elite">("all");

  useEffect(() => {
    if (liveProps.length > 0) {
      setLastUpdate(new Date());
    }
  }, [liveProps]);

  const filtered = liveProps.filter((p) => {
    const ev = Math.max(p.ev_over ?? 0, p.ev_under ?? 0);
    if (filter === "elite") return ev >= 10;
    if (filter === "high") return ev >= 5;
    return true;
  });

  const eliteCount = liveProps.filter((p) => Math.max(p.ev_over ?? 0, p.ev_under ?? 0) >= 10).length;
  const highCount = liveProps.filter((p) => Math.max(p.ev_over ?? 0, p.ev_under ?? 0) >= 5).length;

  return (
    <FadeIn className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Activity size={20} className="text-primary" />
            <h1 className="text-2xl font-bold text-white">Live Props</h1>
            <div className={clsx(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
              connected
                ? "bg-success/20 text-success border border-success/30"
                : "bg-muted/20 text-muted border border-border"
            )}>
              {connected
                ? <><Wifi size={11} /> Live</>
                : <><WifiOff size={11} /> Connecting...</>}
            </div>
          </div>
          <p className="text-muted text-sm mt-1">
            Real-time prop feed via WebSocket — updates every 30 seconds
          </p>
        </div>

        {lastUpdate && (
          <div className="flex items-center gap-1.5 text-muted text-xs">
            <Clock size={12} />
            <span>Updated {format(lastUpdate, "HH:mm:ss")}</span>
          </div>
        )}
      </div>

      {/* Live stats bar */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Live Props", value: liveProps.length, icon: Activity, color: "text-white" },
          { label: "High EV (5%+)", value: highCount, icon: Flame, color: "text-ev-strong" },
          { label: "Elite EV (10%+)", value: eliteCount, icon: Flame, color: "text-ev-elite" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-surface border border-border rounded-xl p-3 flex items-center gap-3">
            <Icon size={16} className={color} />
            <div>
              <p className="text-muted text-xs">{label}</p>
              <CountUp value={value} className={clsx("text-xl font-bold", color)} />
            </div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-1 bg-surface border border-border p-1 rounded-xl w-fit">
        {(["all", "high", "elite"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all",
              filter === f ? "bg-primary text-white" : "text-muted hover:text-white"
            )}
          >
            {f === "all" ? `All (${liveProps.length})` :
             f === "high" ? `High EV (${highCount})` :
             `Elite EV (${eliteCount})`}
          </button>
        ))}
      </div>

      {/* Prop grid */}
      {!connected ? (
        <div className="text-center py-20">
          <div className="flex justify-center gap-1 mb-4">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-2 h-2 rounded-full bg-primary"
                animate={{ y: [0, -8, 0] }}
                transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.15 }}
              />
            ))}
          </div>
          <p className="text-white font-medium">Connecting to live feed...</p>
          <p className="text-muted text-sm mt-1">WebSocket connecting to backend</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <Activity size={36} className="text-muted mx-auto mb-3 opacity-40" />
          <p className="text-white font-medium">No {filter !== "all" ? "high-EV " : ""}props in live feed</p>
          <p className="text-muted text-sm mt-1">
            {filter !== "all"
              ? "Lower the EV filter to see more props"
              : "Waiting for data refresh..."}
          </p>
        </div>
      ) : (
        <StaggerChildren className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <AnimatePresence mode="popLayout">
            {filtered.map((prop) => (
              <StaggerItem key={prop.id}>
                <PropCard prop={prop} />
              </StaggerItem>
            ))}
          </AnimatePresence>
        </StaggerChildren>
      )}
    </FadeIn>
  );
}
