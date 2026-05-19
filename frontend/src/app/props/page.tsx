"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import PropCard from "@/components/props/PropCard";
import PropFilters from "@/components/props/PropFilters";
import EVChart from "@/components/charts/EVChart";
import { useTopProps, useMispriced, useBestBets } from "@/hooks/useProps";
import { getParlayBuilder, getSharpAction } from "@/lib/api";
import type { FilterState } from "@/lib/types";
import useSWR from "swr";
import { clsx } from "clsx";
import { Zap, AlertCircle, Flame, Shield, Target } from "lucide-react";

const TABS = [
  { id: "all", label: "All Props", icon: Target },
  { id: "best-bets", label: "Best Bets", icon: Flame },
  { id: "mispriced", label: "Mispriced", icon: AlertCircle },
  { id: "sharp", label: "Sharp Action", icon: Shield },
  { id: "parlay", label: "Parlay Builder", icon: Zap },
];

const DEFAULT_FILTERS: FilterState = {
  sport: "ALL",
  stat_type: "",
  min_ev: 0,
  show_stale: false,
  show_boosted: false,
  risk_level: "ALL",
};

function ParlayBuilderTab() {
  const [legCount, setLegCount] = useState(2);
  const [sport, setSport] = useState("");
  const { data, isLoading } = useSWR(
    ["parlay", legCount, sport],
    () => getParlayBuilder({ leg_count: legCount, sport: sport || undefined }),
    { refreshInterval: 60000 }
  );

  const payouts: Record<number, number> = { 2: 3, 3: 5, 4: 10, 5: 20, 6: 40 };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div>
          <label className="text-xs text-muted block mb-1">Legs</label>
          <div className="flex gap-1 bg-surface-2 p-1 rounded-lg">
            {[2, 3, 4, 5, 6].map((n) => (
              <button
                key={n}
                onClick={() => setLegCount(n)}
                className={clsx(
                  "px-3 py-1.5 rounded text-xs font-semibold transition-all",
                  legCount === n ? "bg-primary text-white" : "text-muted hover:text-white"
                )}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Sport</label>
          <select
            value={sport}
            onChange={(e) => setSport(e.target.value)}
            className="px-3 py-2 bg-surface-2 border border-border rounded-lg text-xs text-white focus:outline-none"
          >
            {["All Sports", "NBA", "NFL", "MLB", "NHL"].map((s) => (
              <option key={s} value={s === "All Sports" ? "" : s}>{s}</option>
            ))}
          </select>
        </div>
        {data && (
          <div className="ml-auto flex items-center gap-6">
            <div className="text-center">
              <p className="text-muted text-xs">Payout</p>
              <p className="text-white font-bold text-lg">{payouts[legCount]}x</p>
            </div>
            <div className="text-center">
              <p className="text-muted text-xs">Win Prob</p>
              <p className="text-warning font-bold text-lg">
                {(data.combined_probability * 100).toFixed(1)}%
              </p>
            </div>
            <div className="text-center">
              <p className="text-muted text-xs">Parlay EV</p>
              <p className={clsx(
                "font-bold text-lg",
                data.combined_ev > 0 ? "text-success" : "text-danger"
              )}>
                {data.combined_ev > 0 ? "+" : ""}{data.combined_ev.toFixed(1)}%
              </p>
            </div>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: legCount }).map((_, i) => (
            <div key={i} className="h-16 bg-surface border border-border rounded-xl animate-pulse" />
          ))}
        </div>
      ) : data?.legs.map((leg, i) => (
        <div key={i} className="flex items-center gap-4 bg-surface border border-border rounded-xl p-4">
          <span className="w-6 h-6 rounded-full bg-primary/20 text-primary text-xs flex items-center justify-center font-bold flex-shrink-0">
            {i + 1}
          </span>
          <div className="flex-1">
            <p className="text-white font-semibold text-sm">{leg.player_name}</p>
            <p className="text-muted text-xs">{leg.sport} • {leg.stat_type}</p>
          </div>
          <div className="text-center">
            <p className="text-muted text-xs">Line</p>
            <p className="text-white font-bold">{leg.line}</p>
          </div>
          <div className={clsx(
            "px-3 py-1.5 rounded-lg text-xs font-bold border",
            leg.direction === "over"
              ? "bg-success/20 border-success/30 text-success"
              : "bg-danger/20 border-danger/30 text-danger"
          )}>
            {leg.direction.toUpperCase()}
          </div>
          <div className="text-right">
            <p className="text-muted text-xs">EV</p>
            <p className="text-ev-good font-bold text-sm">+{leg.ev_pct.toFixed(1)}%</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function SharpActionTab() {
  const { data: props = [], isLoading } = useSWR("sharp-action", getSharpAction, { refreshInterval: 30000 });
  return isLoading ? (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-72 bg-surface border border-border rounded-xl animate-pulse" />
      ))}
    </div>
  ) : (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {props.map((p) => <PropCard key={p.id} prop={p} />)}
    </div>
  );
}

function PropsContent() {
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") ?? "all";
  const [activeTab, setActiveTab] = useState(initialTab);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  const { data: allProps = [], isLoading: loadingAll } = useTopProps(
    activeTab === "all" ? filters : {}
  );
  const { data: bestBets = [], isLoading: loadingBest } = useBestBets(
    activeTab === "best-bets" ? (filters.sport !== "ALL" ? filters.sport : undefined) : undefined
  );
  const { data: mispriced = [], isLoading: loadingMispriced } = useMispriced();

  const activeProps =
    activeTab === "all" ? allProps :
    activeTab === "best-bets" ? bestBets :
    activeTab === "mispriced" ? mispriced :
    [];

  const loading =
    activeTab === "all" ? loadingAll :
    activeTab === "best-bets" ? loadingBest :
    activeTab === "mispriced" ? loadingMispriced :
    false;

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Props</h1>
        <p className="text-muted text-sm mt-1">All active props ranked by expected value</p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-surface border border-border p-1 rounded-xl w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              activeTab === id
                ? "bg-primary text-white shadow"
                : "text-muted hover:text-white"
            )}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Filters — only for all/best-bets */}
      {(activeTab === "all" || activeTab === "best-bets") && (
        <PropFilters filters={filters} onChange={setFilters} />
      )}

      {/* Chart for all props view */}
      {activeTab === "all" && activeProps.length > 0 && (
        <EVChart props={activeProps.slice(0, 20)} />
      )}

      {/* Content */}
      {activeTab === "parlay" ? (
        <ParlayBuilderTab />
      ) : activeTab === "sharp" ? (
        <SharpActionTab />
      ) : loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="h-72 bg-surface border border-border rounded-xl animate-pulse" />
          ))}
        </div>
      ) : activeProps.length === 0 ? (
        <div className="text-center py-20">
          <Target size={40} className="text-muted mx-auto mb-3 opacity-40" />
          <p className="text-white font-medium">No props found</p>
          <p className="text-muted text-sm mt-1">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {activeProps.map((p) => <PropCard key={p.id} prop={p} />)}
        </div>
      )}
    </div>
  );
}

export default function PropsPage() {
  return (
    <Suspense>
      <PropsContent />
    </Suspense>
  );
}
