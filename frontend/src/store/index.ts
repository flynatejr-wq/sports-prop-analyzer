/**
 * Zustand global store — single source of truth for app-wide state.
 * Avoids prop-drilling and keeps SWR for server state, Zustand for UI state.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { FilterState, Sport } from "@/lib/types";

// ── Filter state ──────────────────────────────────────────────────────────────

interface FilterStore {
  filters: FilterState;
  setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  setFilters: (filters: Partial<FilterState>) => void;
  resetFilters: () => void;
}

const DEFAULT_FILTERS: FilterState = {
  sport: "ALL",
  stat_type: "",
  min_ev: 0,
  show_stale: false,
  show_boosted: false,
  risk_level: "ALL",
};

export const useFilterStore = create<FilterStore>()(
  persist(
    (set) => ({
      filters: DEFAULT_FILTERS,
      setFilter: (key, value) =>
        set((state) => ({ filters: { ...state.filters, [key]: value } })),
      setFilters: (partial) =>
        set((state) => ({ filters: { ...state.filters, ...partial } })),
      resetFilters: () => set({ filters: DEFAULT_FILTERS }),
    }),
    {
      name: "propedge-filters",
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// ── Bankroll state ────────────────────────────────────────────────────────────

interface BankrollStore {
  bankroll: number;
  unitSize: number;
  kellyFraction: number;
  totalProfit: number;
  totalBets: number;
  setBankroll: (amount: number) => void;
  setUnitSize: (size: number) => void;
  setKellyFraction: (f: number) => void;
  addResult: (profitLoss: number) => void;
  resetStats: () => void;
}

export const useBankrollStore = create<BankrollStore>()(
  persist(
    (set) => ({
      bankroll: 1000,
      unitSize: 10,
      kellyFraction: 0.25,
      totalProfit: 0,
      totalBets: 0,
      setBankroll: (amount) => set({ bankroll: amount }),
      setUnitSize: (size) => set({ unitSize: size }),
      setKellyFraction: (f) => set({ kellyFraction: f }),
      addResult: (pnl) =>
        set((state) => ({
          totalProfit: state.totalProfit + pnl,
          totalBets: state.totalBets + 1,
          bankroll: state.bankroll + pnl,
        })),
      resetStats: () => set({ totalProfit: 0, totalBets: 0 }),
    }),
    {
      name: "propedge-bankroll",
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// ── Alert / notification state ────────────────────────────────────────────────

interface ToastMessage {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message?: string;
}

interface NotificationStore {
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  toasts: [],
  addToast: (toast) =>
    set((state) => ({
      toasts: [
        ...state.toasts.slice(-4), // keep last 5
        { ...toast, id: Date.now().toString() },
      ],
    })),
  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  clearAll: () => set({ toasts: [] }),
}));

// ── UI preferences ────────────────────────────────────────────────────────────

interface UIStore {
  sidebarCollapsed: boolean;
  activeTab: string;
  viewMode: "grid" | "table";
  toggleSidebar: () => void;
  setActiveTab: (tab: string) => void;
  setViewMode: (mode: "grid" | "table") => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      activeTab: "all",
      viewMode: "grid",
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setActiveTab: (tab) => set({ activeTab: tab }),
      setViewMode: (mode) => set({ viewMode: mode }),
    }),
    { name: "propedge-ui", storage: createJSONStorage(() => localStorage) }
  )
);
