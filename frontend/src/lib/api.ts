import type {
  Prop,
  AnalyticsSummary,
  HitRateRow,
  OddsMovement,
  ParlayBuilder,
  UserPick,
  KellyResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Props ─────────────────────────────────────────────────────────────────────

export function getTopProps(params?: {
  sport?: string;
  stat_type?: string;
  min_ev?: number;
  limit?: number;
}): Promise<Prop[]> {
  const q = new URLSearchParams();
  if (params?.sport) q.set("sport", params.sport);
  if (params?.stat_type) q.set("stat_type", params.stat_type);
  if (params?.min_ev != null) q.set("min_ev", String(params.min_ev));
  if (params?.limit) q.set("limit", String(params.limit));
  return apiFetch<Prop[]>(`/api/v1/props/top?${q}`);
}

export function getBestBets(sport?: string): Promise<Prop[]> {
  const q = sport ? `?sport=${sport}` : "";
  return apiFetch<Prop[]>(`/api/v1/props/best-bets${q}`);
}

export function getMispricedProps(): Promise<Prop[]> {
  return apiFetch<Prop[]>("/api/v1/props/mispriced");
}

export function getSharpAction(): Promise<Prop[]> {
  return apiFetch<Prop[]>("/api/v1/props/sharp-action");
}

export function getPropDetail(id: number): Promise<Prop> {
  return apiFetch<Prop>(`/api/v1/props/${id}`);
}

export function searchPlayerProps(name: string): Promise<Prop[]> {
  return apiFetch<Prop[]>(`/api/v1/props/search/${encodeURIComponent(name)}`);
}

export function triggerRefresh(): Promise<{ message: string; status: string }> {
  return apiFetch("/api/v1/props/refresh", { method: "POST" });
}

export function getParlayBuilder(params: {
  leg_count?: number;
  sport?: string;
  min_ev_per_leg?: number;
}): Promise<ParlayBuilder> {
  const q = new URLSearchParams();
  if (params.leg_count) q.set("leg_count", String(params.leg_count));
  if (params.sport) q.set("sport", params.sport);
  if (params.min_ev_per_leg) q.set("min_ev_per_leg", String(params.min_ev_per_leg));
  return apiFetch<ParlayBuilder>(`/api/v1/props/parlay-builder?${q}`);
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>("/api/v1/analytics/summary");
}

export function getHitRates(sport?: string): Promise<HitRateRow[]> {
  const q = sport ? `?sport=${sport}` : "";
  return apiFetch<HitRateRow[]>(`/api/v1/analytics/hit-rates${q}`);
}

export function getOddsMovement(propId: number): Promise<OddsMovement[]> {
  return apiFetch<OddsMovement[]>(`/api/v1/analytics/odds-movement/${propId}`);
}

export function getKellySizing(params: {
  bankroll: number;
  prob_win: number;
  american_odds?: number;
  fraction?: number;
  max_pct?: number;
}): Promise<KellyResponse> {
  return apiFetch<KellyResponse>("/api/v1/analytics/kelly", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ── Picks ─────────────────────────────────────────────────────────────────────

export function getPicks(): Promise<UserPick[]> {
  return apiFetch<UserPick[]>("/api/v1/analytics/picks");
}

export function addPick(params: {
  prop_id: number;
  direction: string;
  stake: number;
  odds?: number;
  ev_at_pick?: number;
}): Promise<{ id: number }> {
  return apiFetch("/api/v1/analytics/picks", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
