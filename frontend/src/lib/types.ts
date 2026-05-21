export type Sport = "NBA" | "NFL" | "MLB" | "NHL" | "NCAAB" | "NCAAF" | "WNBA";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type EdgeClass = "ELITE" | "STRONG" | "GOOD" | "SLIGHT" | "MARGINAL" | "NEGATIVE";

export interface Prop {
  id: number;
  player_name: string;
  team?: string | null;
  sport: Sport;
  stat_type: string;
  line: number;
  source?: string | null;
  ev_over?: number | null;
  ev_under?: number | null;
  edge_classification?: EdgeClass | null;
  consensus_line?: number | null;
  line_discrepancy?: number | null;
  fair_value?: number | null;
  implied_prob_over?: number | null;
  implied_prob_under?: number | null;
  fair_prob_over?: number | null;
  is_stale: boolean;
  is_boosted: boolean;
  last_5_avg?: number | null;
  season_avg?: number | null;
  hit_rate_over?: number | null;
  ml_projection?: number | null;
  ml_confidence?: number | null;
  ml_risk_level?: RiskLevel | null;
  game_date?: string | null;
  opponent?: string | null;
  status: string;
  image_url?: string | null;
  home_avg?: number | null;
  away_avg?: number | null;
  volatility_score?: number | null;
  notes?: string | null;
  ai_insight?: string | null;
}

export interface AnalyticsSummary {
  active_props: number;
  high_ev_props: number;
  stale_lines: number;
  picks_tracked: number;
  wins: number;
  losses: number;
  hit_rate: number;
  total_profit_units: number;
  roi_pct: number;
}

export interface HitRateRow {
  stat_type: string;
  total: number;
  hits: number;
  hit_rate: number;
  avg_ev: number;
}

export interface OddsMovement {
  timestamp: string;
  sportsbook: string;
  line: number;
  over_odds?: number;
  under_odds?: number;
}

export interface ParlayBuilder {
  legs: ParlayLeg[];
  leg_count: number;
  payout_multiplier: number;
  combined_probability: number;
  combined_ev: number;
  expected_units: number;
}

export interface ParlayLeg {
  player_name: string;
  stat_type: string;
  line: number;
  direction: "over" | "under";
  ev_pct: number;
  prob: number;
  sport: string;
}

export interface UserPick {
  id: number;
  prop_id: number;
  direction: "over" | "under";
  stake: number;
  odds?: number;
  ev_at_pick?: number;
  result: string;
  profit_loss?: number;
  created_at: string;
}

export interface KellyResponse {
  recommended_stake: number;
  kelly_fraction: number;
  expected_profit: number;
  risk_pct: number;
}

export interface FilterState {
  sport: Sport | "ALL";
  stat_type: string;
  min_ev: number;
  show_stale: boolean;
  show_boosted: boolean;
  risk_level: RiskLevel | "ALL";
}
