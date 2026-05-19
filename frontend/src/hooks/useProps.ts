import useSWR from "swr";
import { getTopProps, getBestBets, getMispricedProps, getAnalyticsSummary } from "@/lib/api";
import type { FilterState } from "@/lib/types";

const REFRESH_MS = 30_000;

export function useTopProps(filters: Partial<FilterState> = {}) {
  return useSWR(
    ["top-props", filters],
    () =>
      getTopProps({
        sport: filters.sport !== "ALL" ? filters.sport : undefined,
        stat_type: filters.stat_type,
        min_ev: filters.min_ev,
        limit: 50,
      }),
    { refreshInterval: REFRESH_MS, revalidateOnFocus: false }
  );
}

export function useBestBets(sport?: string) {
  return useSWR(
    ["best-bets", sport],
    () => getBestBets(sport),
    { refreshInterval: REFRESH_MS }
  );
}

export function useMispriced() {
  return useSWR("mispriced", getMispricedProps, { refreshInterval: 60_000 });
}

export function useAnalyticsSummary() {
  return useSWR("analytics-summary", getAnalyticsSummary, {
    refreshInterval: 60_000,
  });
}
