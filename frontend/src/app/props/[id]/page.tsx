"use client";
import { use, useState } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, TrendingUp, TrendingDown, Brain, BarChart2,
  AlertTriangle, Zap, Target, Calendar, Shield, RefreshCw,
  CheckCircle, XCircle, Loader2,
} from "lucide-react";
import { clsx } from "clsx";
import { getPropDetail, getOddsMovement, getKellySizing, addPick } from "@/lib/api";
import OddsMovementChart from "@/components/charts/OddsMovement";
import { useNotificationStore } from "@/store";
import type { Prop } from "@/lib/types";

// ── Helpers ──────────────────────────────────────────────────────────────────

const EDGE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  ELITE:    { bg: "bg-ev-elite/10",    text: "text-ev-elite",    border: "border-ev-elite/30"   },
  STRONG:   { bg: "bg-ev-strong/10",   text: "text-ev-strong",   border: "border-ev-strong/30"  },
  GOOD:     { bg: "bg-ev-good/10",     text: "text-ev-good",     border: "border-ev-good/30"    },
  SLIGHT:   { bg: "bg-primary/10",     text: "text-primary",     border: "border-primary/30"    },
  MARGINAL: { bg: "bg-surface-2",      text: "text-muted",       border: "border-border"        },
  NEGATIVE: { bg: "bg-danger/10",      text: "text-danger",      border: "border-danger/30"     },
};

const SOURCE_LABELS: Record<string, string> = {
  prizepicks: "PrizePicks",
  oddsapi:    "Multi-Book Consensus",
  underdog:   "Underdog Fantasy",
};

const SPORT_COLORS: Record<string, string> = {
  NBA:  "bg-orange-500/20 text-orange-400",
  NFL:  "bg-blue-500/20 text-blue-400",
  MLB:  "bg-red-500/20 text-red-400",
  NHL:  "bg-cyan-500/20 text-cyan-400",
};

function StatBox({ label, value, sub, highlight = false }: {
  label: string; value: string | number; sub?: string; highlight?: boolean;
}) {
  return (
    <div className="bg-surface-2 rounded-xl p-4 text-center">
      <p className="text-muted text-xs mb-1">{label}</p>
      <p className={clsx("text-xl font-bold font-mono", highlight ? "text-ev-good" : "text-white")}>
        {value}
      </p>
      {sub && <p className="text-muted text-[10px] mt-0.5">{sub}</p>}
    </div>
  );
}

function ProbabilityBar({ over, under }: { over: number; under: number }) {
  const op = Math.round(over * 100);
  const up = Math.round(under * 100);
  return (
    <div>
      <div className="flex justify-between text-xs text-muted mb-1.5">
        <span className="text-success font-medium">OVER {op}%</span>
        <span className="text-danger font-medium">UNDER {up}%</span>
      </div>
      <div className="h-3 rounded-full overflow-hidden flex bg-surface-2 relative">
        <div className="bg-success/70 transition-all duration-500" style={{ width: `${op}%` }} />
        <div className="flex-1 bg-danger/50" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white text-[10px] font-bold mix-blend-screen">
            {op}/{up}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Kelly Calculator section ──────────────────────────────────────────────────

function KellySection({ prop }: { prop: Prop }) {
  const { addToast } = useNotificationStore();
  const [bankroll, setBankroll] = useState(1000);
  const [fraction, setFraction] = useState(0.25);
  const [odds, setOdds] = useState(-110);
  const [direction, setDirection] = useState<"over" | "under">(
    (prop.ev_over ?? 0) >= (prop.ev_under ?? 0) ? "over" : "under"
  );
  const [pickAdding, setPickAdding] = useState(false);
  const [pickAdded, setPickAdded] = useState(false);

  const prob = direction === "over"
    ? (prop.implied_prob_over ?? 0.52)
    : (prop.implied_prob_under ?? 0.48);

  const { data: kelly, isLoading } = useSWR(
    ["kelly", bankroll, prob, odds, fraction],
    () => getKellySizing({ bankroll, prob_win: prob, american_odds: odds, fraction }),
    { revalidateOnFocus: false }
  );

  async function handleAddPick() {
    setPickAdding(true);
    try {
      await addPick({
        prop_id: prop.id,
        direction,
        stake: kelly?.recommended_stake ?? 1,
        odds,
        ev_at_pick: direction === "over" ? (prop.ev_over ?? 0) : (prop.ev_under ?? 0),
      });
      setPickAdded(true);
      addToast({ type: "success", title: "Pick saved to tracker" });
    } catch {
      addToast({ type: "error", title: "Failed to save pick" });
    } finally {
      setPickAdding(false);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Target size={16} className="text-primary" />
        <h3 className="text-white font-semibold text-sm">Kelly Sizing & Track Pick</h3>
      </div>

      {/* Direction toggle */}
      <div className="flex gap-2">
        {(["over", "under"] as const).map((d) => (
          <button
            key={d}
            onClick={() => setDirection(d)}
            className={clsx(
              "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold border transition-all",
              direction === d
                ? d === "over"
                  ? "bg-success/20 text-success border-success/40"
                  : "bg-danger/20 text-danger border-danger/40"
                : "bg-surface-2 text-muted border-border hover:text-white"
            )}
          >
            {d === "over" ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {d.toUpperCase()}
            {d === "over" && prop.ev_over && prop.ev_over > 0 && (
              <span className="text-ev-good text-[10px] font-mono">+{prop.ev_over.toFixed(1)}%</span>
            )}
            {d === "under" && prop.ev_under && prop.ev_under > 0 && (
              <span className="text-ev-good text-[10px] font-mono">+{prop.ev_under.toFixed(1)}%</span>
            )}
          </button>
        ))}
      </div>

      {/* Inputs */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-muted block mb-1">Bankroll ($)</label>
          <input
            type="number" step={100} min={0} value={bankroll}
            onChange={(e) => setBankroll(parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary"
          />
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Odds (American)</label>
          <input
            type="number" step={5} value={odds}
            onChange={(e) => setOdds(parseFloat(e.target.value) || -110)}
            className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      {/* Kelly fraction */}
      <div>
        <label className="text-xs text-muted block mb-1.5">Kelly Fraction</label>
        <div className="flex gap-2">
          {[{ v: 0.25, l: "¼ Kelly" }, { v: 0.5, l: "½ Kelly" }, { v: 1.0, l: "Full Kelly" }].map(({ v, l }) => (
            <button
              key={v}
              onClick={() => setFraction(v)}
              className={clsx(
                "flex-1 py-1.5 rounded-lg text-xs font-medium border transition-all",
                fraction === v ? "bg-primary text-white border-primary" : "bg-surface-2 text-muted border-border hover:text-white"
              )}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Result */}
      {isLoading ? (
        <div className="h-16 bg-surface-2 rounded-xl animate-pulse" />
      ) : kelly ? (
        <div className="grid grid-cols-3 gap-3">
          <StatBox label="Stake" value={`$${kelly.recommended_stake.toFixed(2)}`} highlight />
          <StatBox label="Expected Profit" value={`$${kelly.expected_profit.toFixed(2)}`} highlight />
          <StatBox label="Risk %" value={`${kelly.risk_pct}%`} />
        </div>
      ) : null}

      {/* Add to picks */}
      <button
        onClick={handleAddPick}
        disabled={pickAdding || pickAdded}
        className={clsx(
          "w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all",
          pickAdded
            ? "bg-success/20 text-success border border-success/30"
            : "bg-primary text-white hover:bg-primary-hover"
        )}
      >
        {pickAdding ? (
          <><Loader2 size={14} className="animate-spin" /> Saving...</>
        ) : pickAdded ? (
          <><CheckCircle size={14} /> Pick Saved to Tracker</>
        ) : (
          <><Target size={14} /> Track this Pick</>
        )}
      </button>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PropDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const propId = parseInt(id, 10);
  const router = useRouter();

  const { data: prop, isLoading, error } = useSWR(
    `prop-${propId}`,
    () => getPropDetail(propId),
    { refreshInterval: 60000 }
  );

  const { data: movement = [] } = useSWR(
    prop ? `movement-${propId}` : null,
    () => getOddsMovement(propId),
    { refreshInterval: 120000 }
  );

  if (isLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="h-8 w-48 bg-surface rounded animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="h-64 bg-surface border border-border rounded-xl animate-pulse" />
            <div className="h-48 bg-surface border border-border rounded-xl animate-pulse" />
          </div>
          <div className="space-y-4">
            <div className="h-48 bg-surface border border-border rounded-xl animate-pulse" />
            <div className="h-64 bg-surface border border-border rounded-xl animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !prop) {
    return (
      <div className="text-center py-20">
        <XCircle size={40} className="text-danger mx-auto mb-3 opacity-60" />
        <p className="text-white font-medium text-lg">Prop not found</p>
        <p className="text-muted text-sm mt-1">This prop may have expired or been removed</p>
        <button
          onClick={() => router.back()}
          className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors"
        >
          Go Back
        </button>
      </div>
    );
  }

  const evOver = prop.ev_over ?? 0;
  const evUnder = prop.ev_under ?? 0;
  const bestEv = Math.max(evOver, evUnder);
  const bestDir = evOver >= evUnder ? "OVER" : "UNDER";
  const edge = prop.edge_classification ?? "MARGINAL";
  const edgeColor = EDGE_COLORS[edge] ?? EDGE_COLORS.MARGINAL;
  const probOver = prop.implied_prob_over ?? 0.5;
  const probUnder = prop.implied_prob_under ?? (1 - probOver);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back + breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-muted text-sm hover:text-white transition-colors"
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <span className="text-border">/</span>
        <span className="text-muted text-sm">Props</span>
        <span className="text-border">/</span>
        <span className="text-white text-sm font-medium">{prop.player_name}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Left: main detail ──────────────────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-5">

          {/* Hero card */}
          <div className={clsx(
            "bg-surface border rounded-xl overflow-hidden",
            edge === "ELITE" ? "border-ev-elite/30" :
            edge === "STRONG" ? "border-ev-strong/30" :
            edge === "GOOD" ? "border-ev-good/30" :
            "border-border"
          )}>
            {/* Top gradient bar */}
            <div className={clsx(
              "h-1",
              edge === "ELITE"  ? "bg-gradient-to-r from-ev-elite to-transparent" :
              edge === "STRONG" ? "bg-gradient-to-r from-ev-strong to-transparent" :
              edge === "GOOD"   ? "bg-gradient-to-r from-ev-good to-transparent" :
              "bg-transparent"
            )} />

            <div className="p-6">
              {/* Player header */}
              <div className="flex items-start gap-4 mb-5">
                {prop.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={prop.image_url}
                    alt={prop.player_name}
                    className="w-16 h-16 rounded-full object-cover bg-surface-2 ring-2 ring-border flex-shrink-0"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/40 to-primary/10 flex-shrink-0 flex items-center justify-center text-xl font-bold text-primary ring-2 ring-border">
                    {prop.player_name.charAt(0)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h1 className="text-white text-2xl font-bold">{prop.player_name}</h1>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className={clsx("text-xs font-bold px-2 py-0.5 rounded", SPORT_COLORS[prop.sport] ?? "bg-surface-2 text-muted")}>
                      {prop.sport}
                    </span>
                    {prop.team && <span className="text-muted text-sm">{prop.team}</span>}
                    {prop.opponent && (
                      <span className="text-muted text-sm">vs {prop.opponent}</span>
                    )}
                    {prop.game_date && (
                      <span className="flex items-center gap-1 text-muted text-xs">
                        <Calendar size={11} /> {prop.game_date}
                      </span>
                    )}
                    <span className="text-muted text-xs border border-border rounded px-1.5 py-0.5">
                      {SOURCE_LABELS[prop.source ?? "oddsapi"] ?? "Multi-Book"}
                    </span>
                  </div>
                </div>

                {/* EV badge */}
                <div className={clsx(
                  "flex-shrink-0 text-right px-4 py-3 rounded-xl border",
                  edgeColor.bg, edgeColor.text, edgeColor.border
                )}>
                  <p className="text-3xl font-bold font-mono">
                    {bestEv > 0 ? `+${bestEv.toFixed(1)}%` : `${bestEv.toFixed(1)}%`}
                  </p>
                  <p className="text-xs font-medium opacity-80">{edge} EDGE</p>
                </div>
              </div>

              {/* Main stat line */}
              <div className="grid grid-cols-3 gap-4 mb-5 p-4 bg-surface-2 rounded-xl">
                <div className="text-center">
                  <p className="text-muted text-xs mb-1">{prop.stat_type}</p>
                  <p className="text-white text-4xl font-bold font-mono">{prop.line}</p>
                  <p className="text-muted text-xs mt-1">Prop Line</p>
                </div>
                <div className="text-center border-x border-border">
                  <p className="text-muted text-xs mb-1">Consensus</p>
                  <p className={clsx(
                    "text-3xl font-bold font-mono",
                    prop.consensus_line ? "text-white" : "text-muted"
                  )}>
                    {prop.consensus_line?.toFixed(1) ?? "—"}
                  </p>
                  {prop.line_discrepancy != null && Math.abs(prop.line_discrepancy) > 0.05 && (
                    <p className={clsx(
                      "text-sm font-mono mt-1",
                      prop.line_discrepancy < 0 ? "text-success" : "text-danger"
                    )}>
                      {prop.line_discrepancy > 0 ? "+" : ""}{prop.line_discrepancy.toFixed(2)} gap
                    </p>
                  )}
                </div>
                <div className="text-center">
                  <p className="text-muted text-xs mb-1">Best Direction</p>
                  <div className={clsx(
                    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-bold mt-1",
                    bestDir === "OVER" ? "bg-success/20 text-success" : "bg-danger/20 text-danger"
                  )}>
                    {bestDir === "OVER" ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    {bestDir}
                  </div>
                  <p className="text-muted text-xs mt-1 font-mono">
                    {bestEv > 0 ? `+${bestEv.toFixed(2)}% EV` : `${bestEv.toFixed(2)}% EV`}
                  </p>
                </div>
              </div>

              {/* EV breakdown */}
              <div className="grid grid-cols-2 gap-3 mb-5">
                <div className={clsx(
                  "p-3 rounded-xl border",
                  evOver > 0 ? "bg-success/10 border-success/20" : "bg-surface-2 border-border"
                )}>
                  <div className="flex items-center gap-2 mb-1">
                    <TrendingUp size={14} className={evOver > 0 ? "text-success" : "text-muted"} />
                    <span className={clsx("text-xs font-semibold", evOver > 0 ? "text-success" : "text-muted")}>
                      OVER Edge
                    </span>
                  </div>
                  <p className={clsx("text-2xl font-bold font-mono", evOver > 0 ? "text-success" : "text-muted")}>
                    {evOver > 0 ? `+${evOver.toFixed(2)}%` : "—"}
                  </p>
                </div>
                <div className={clsx(
                  "p-3 rounded-xl border",
                  evUnder > 0 ? "bg-danger/10 border-danger/20" : "bg-surface-2 border-border"
                )}>
                  <div className="flex items-center gap-2 mb-1">
                    <TrendingDown size={14} className={evUnder > 0 ? "text-danger" : "text-muted"} />
                    <span className={clsx("text-xs font-semibold", evUnder > 0 ? "text-danger" : "text-muted")}>
                      UNDER Edge
                    </span>
                  </div>
                  <p className={clsx("text-2xl font-bold font-mono", evUnder > 0 ? "text-danger" : "text-muted")}>
                    {evUnder > 0 ? `+${evUnder.toFixed(2)}%` : "—"}
                  </p>
                </div>
              </div>

              {/* Probability bar */}
              <ProbabilityBar over={probOver} under={probUnder} />
            </div>
          </div>

          {/* Historical stats */}
          <div className="bg-surface border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart2 size={16} className="text-primary" />
              <h3 className="text-white font-semibold text-sm">Historical Performance</h3>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatBox
                label="Season Avg"
                value={prop.season_avg?.toFixed(1) ?? "—"}
                sub={prop.stat_type}
              />
              <StatBox
                label="Last 5 Avg"
                value={prop.last_5_avg?.toFixed(1) ?? "—"}
                sub="recent form"
                highlight={prop.last_5_avg != null && prop.season_avg != null && prop.last_5_avg > prop.season_avg}
              />
              <StatBox
                label="Hit Rate OVER"
                value={prop.hit_rate_over != null ? `${(prop.hit_rate_over * 100).toFixed(0)}%` : "—"}
                sub={`of ${prop.line} line`}
                highlight={prop.hit_rate_over != null && prop.hit_rate_over >= 0.6}
              />
              <StatBox
                label="ML Projection"
                value={prop.ml_projection?.toFixed(1) ?? "—"}
                sub={prop.ml_confidence != null ? `${prop.ml_confidence.toFixed(0)}% conf.` : undefined}
                highlight={prop.ml_projection != null}
              />
            </div>

            {(prop.home_avg != null || prop.away_avg != null) && (
              <div className="grid grid-cols-2 gap-3 mt-3">
                {prop.home_avg != null && (
                  <StatBox label="Home Avg" value={prop.home_avg.toFixed(1)} />
                )}
                {prop.away_avg != null && (
                  <StatBox label="Away Avg" value={prop.away_avg.toFixed(1)} />
                )}
              </div>
            )}
          </div>

          {/* Odds movement chart */}
          {movement.length > 1 && (
            <OddsMovementChart
              data={movement}
              ppLine={prop.line}
              title="Odds Movement History"
            />
          )}

          {/* Flags */}
          {(prop.is_stale || prop.is_boosted || prop.ml_risk_level) && (
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Shield size={16} className="text-warning" />
                <h3 className="text-white font-semibold text-sm">Signals & Flags</h3>
              </div>
              <div className="space-y-2">
                {prop.is_stale && (
                  <div className="flex items-start gap-3 p-3 bg-warning/5 border border-warning/20 rounded-lg">
                    <AlertTriangle size={14} className="text-warning mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-warning text-xs font-semibold">Stale Line Detected</p>
                      <p className="text-muted text-xs mt-0.5">
                        The consensus has moved but this book hasn&apos;t updated. Sharp players often target these gaps.
                      </p>
                    </div>
                  </div>
                )}
                {prop.is_boosted && (
                  <div className="flex items-start gap-3 p-3 bg-warning/5 border border-warning/20 rounded-lg">
                    <Zap size={14} className="text-warning mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-warning text-xs font-semibold">Boosted Line</p>
                      <p className="text-muted text-xs mt-0.5">
                        The platform is offering enhanced odds on this prop. Value may be inflated.
                      </p>
                    </div>
                  </div>
                )}
                {prop.ml_risk_level && (
                  <div className={clsx(
                    "flex items-start gap-3 p-3 rounded-lg border",
                    prop.ml_risk_level === "HIGH"   ? "bg-danger/5 border-danger/20" :
                    prop.ml_risk_level === "MEDIUM" ? "bg-warning/5 border-warning/20" :
                    "bg-success/5 border-success/20"
                  )}>
                    <Shield size={14} className={clsx(
                      "mt-0.5 flex-shrink-0",
                      prop.ml_risk_level === "HIGH"   ? "text-danger" :
                      prop.ml_risk_level === "MEDIUM" ? "text-warning" : "text-success"
                    )} />
                    <div>
                      <p className={clsx(
                        "text-xs font-semibold",
                        prop.ml_risk_level === "HIGH"   ? "text-danger" :
                        prop.ml_risk_level === "MEDIUM" ? "text-warning" : "text-success"
                      )}>
                        {prop.ml_risk_level} Risk — ML Assessment
                      </p>
                      <p className="text-muted text-xs mt-0.5">
                        Our model rates this {prop.ml_risk_level?.toLowerCase()} risk
                        {prop.ml_confidence != null ? ` with ${prop.ml_confidence.toFixed(0)}% confidence.` : "."}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Right sidebar ─────────────────────────────────────────────────── */}
        <div className="space-y-5">
          {/* AI Insight */}
          {prop.ai_insight && (
            <div className="bg-surface border border-primary/20 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 bg-primary/20 rounded-lg">
                  <Brain size={14} className="text-primary" />
                </div>
                <h3 className="text-white font-semibold text-sm">AI Analysis</h3>
              </div>
              <p className="text-muted text-sm leading-relaxed">{prop.ai_insight}</p>
              {prop.notes && (
                <p className="text-muted text-xs mt-3 pt-3 border-t border-border italic">
                  {prop.notes}
                </p>
              )}
            </div>
          )}

          {/* Kelly calculator + track pick */}
          <KellySection prop={prop} />

          {/* Quick stats summary */}
          <div className="bg-surface border border-border rounded-xl p-5 space-y-3">
            <h3 className="text-white font-semibold text-sm">Quick Summary</h3>
            {[
              { label: "Edge Classification", value: edge, color: edgeColor.text },
              { label: "Stat Type", value: prop.stat_type, color: "text-white" },
              { label: "Line", value: String(prop.line), color: "text-white" },
              { label: "Consensus", value: prop.consensus_line?.toFixed(1) ?? "N/A", color: "text-white" },
              ...(prop.line_discrepancy != null && Math.abs(prop.line_discrepancy) > 0.05 ? [{
                label: "Line Gap",
                value: `${prop.line_discrepancy > 0 ? "+" : ""}${prop.line_discrepancy.toFixed(2)}`,
                color: prop.line_discrepancy < 0 ? "text-success" : "text-danger",
              }] : []),
              { label: "Source", value: SOURCE_LABELS[prop.source ?? "oddsapi"] ?? "Multi-Book", color: "text-muted" },
              { label: "Status", value: prop.status?.toUpperCase() ?? "ACTIVE", color: "text-success" },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center justify-between text-xs">
                <span className="text-muted">{label}</span>
                <span className={clsx("font-medium", color)}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
