"use client";
import { useState, useEffect, useRef } from "react";
import { Search, RefreshCw, Bell, CheckCircle, Zap, TrendingUp, X, Wifi, WifiOff } from "lucide-react";
import { triggerRefresh, searchPlayerProps } from "@/lib/api";
import { useNotificationStore } from "@/store";
import { propSocket } from "@/lib/websocket";
import type { Prop } from "@/lib/types";

// ── Alert item type ───────────────────────────────────────────────────────────

interface AlertItem {
  id: string;
  title: string;
  message: string;
  ts: Date;
  read: boolean;
}

// ── Notifications dropdown ────────────────────────────────────────────────────

function NotificationsPanel({
  alerts,
  onClear,
  onClose,
}: {
  alerts: AlertItem[];
  onClear: () => void;
  onClose: () => void;
}) {
  return (
    <div className="absolute top-full right-0 mt-2 w-80 bg-surface border border-border rounded-xl shadow-2xl z-50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="text-white font-semibold text-sm">Alerts</span>
        <div className="flex items-center gap-2">
          {alerts.length > 0 && (
            <button onClick={onClear} className="text-muted text-xs hover:text-white transition-colors">
              Clear all
            </button>
          )}
          <button onClick={onClose} className="text-muted hover:text-white transition-colors">
            <X size={14} />
          </button>
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="py-8 text-center">
          <Bell size={24} className="text-muted mx-auto mb-2 opacity-40" />
          <p className="text-muted text-sm">No recent alerts</p>
          <p className="text-muted text-xs mt-1">High-EV props will appear here</p>
        </div>
      ) : (
        <div className="max-h-80 overflow-y-auto">
          {alerts.map((a) => (
            <div
              key={a.id}
              className="flex items-start gap-3 px-4 py-3 border-b border-border/50 hover:bg-surface-2 transition-colors"
            >
              <div className="p-1.5 bg-primary/20 rounded-lg flex-shrink-0 mt-0.5">
                <Zap size={12} className="text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-xs font-semibold">{a.title}</p>
                <p className="text-muted text-[10px] mt-0.5 line-clamp-2">{a.message}</p>
                <p className="text-muted text-[10px] mt-1 opacity-60">
                  {a.ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Navbar ────────────────────────────────────────────────────────────────

export default function Navbar() {
  const { addToast } = useNotificationStore();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Prop[]>([]);
  const [searching, setSearching] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshDone, setRefreshDone] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [showAlerts, setShowAlerts] = useState(false);
  const alertsRef = useRef<HTMLDivElement>(null);
  const unreadCount = alerts.filter((a) => !a.read).length;

  // Track WS connection and incoming alerts
  useEffect(() => {
    const unsub = propSocket.subscribe((msg) => {
      if (msg.type === "alert") {
        const item: AlertItem = {
          id: Date.now().toString(),
          title: msg.data.title,
          message: msg.data.message,
          ts: new Date(),
          read: false,
        };
        setAlerts((prev) => [item, ...prev].slice(0, 20));
        addToast({ type: "info", title: msg.data.title, message: msg.data.message });
      }
      // Detect connection by any message
      setWsConnected(true);
    });

    // Poll connection state
    const interval = setInterval(() => {
      // @ts-ignore — access internal ws state
      const ws = (propSocket as unknown as { ws: WebSocket | null }).ws;
      setWsConnected(ws?.readyState === WebSocket.OPEN);
    }, 3000);

    return () => {
      unsub();
      clearInterval(interval);
    };
  }, [addToast]);

  // Close alerts panel on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (alertsRef.current && !alertsRef.current.contains(e.target as Node)) {
        setShowAlerts(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setQuery(val);
    if (val.length >= 3) {
      setSearching(true);
      try {
        const props = await searchPlayerProps(val);
        setResults(props.slice(0, 6));
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    } else {
      setResults([]);
    }
  }

  async function handleRefresh() {
    if (refreshing) return;
    setRefreshing(true);
    setRefreshDone(false);
    try {
      await triggerRefresh();
      setRefreshDone(true);
      addToast({ type: "success", title: "Refresh queued", message: "Data will update in ~30s" });
      setTimeout(() => setRefreshDone(false), 3000);
    } catch {
      addToast({ type: "error", title: "Refresh failed" });
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <header className="h-14 bg-surface border-b border-border flex items-center px-6 gap-4 sticky top-0 z-10">
      {/* Search */}
      <div className="relative flex-1 max-w-md">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          type="text"
          value={query}
          onChange={handleSearch}
          placeholder="Search player props..."
          className="w-full pl-9 pr-4 py-2 bg-surface-2 border border-border rounded-lg text-sm text-white placeholder-muted focus:outline-none focus:border-primary transition-colors"
        />
        {/* Searching spinner */}
        {searching && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-3 h-3 border border-muted border-t-primary rounded-full animate-spin" />
          </div>
        )}
        {/* Search dropdown */}
        {results.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-surface border border-border rounded-xl shadow-2xl z-50 overflow-hidden">
            {results.map((p) => {
              const bestEv = Math.max(p.ev_over ?? 0, p.ev_under ?? 0);
              return (
                <a
                  key={p.id}
                  href={`/props/${p.id}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-surface-2 transition-colors border-b border-border/50 last:border-0"
                  onClick={() => { setResults([]); setQuery(""); }}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary flex-shrink-0">
                      {p.player_name.charAt(0)}
                    </div>
                    <div>
                      <p className="text-white text-sm font-medium">{p.player_name}</p>
                      <p className="text-muted text-xs">{p.sport} · {p.stat_type} · {p.line}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {bestEv > 0 && (
                      <span className="text-ev-good text-xs font-bold font-mono">+{bestEv.toFixed(1)}%</span>
                    )}
                    <TrendingUp size={12} className="text-muted" />
                  </div>
                </a>
              );
            })}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 ml-auto">
        {/* WS status */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border border-border">
          {wsConnected
            ? <><Wifi size={11} className="text-success" /><span className="text-muted">Live</span></>
            : <><WifiOff size={11} className="text-muted" /><span className="text-muted">Offline</span></>}
        </div>

        {/* Refresh */}
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 bg-surface-2 border border-border rounded-lg text-sm transition-all disabled:opacity-60 hover:border-primary/40"
        >
          {refreshDone ? (
            <>
              <CheckCircle size={14} className="text-success" />
              <span className="text-success">Done</span>
            </>
          ) : (
            <>
              <RefreshCw size={14} className={refreshing ? "animate-spin text-primary" : "text-muted"} />
              <span className={refreshing ? "text-primary" : "text-muted"}>{refreshing ? "Refreshing..." : "Refresh"}</span>
            </>
          )}
        </button>

        {/* Notifications */}
        <div className="relative" ref={alertsRef}>
          <button
            onClick={() => setShowAlerts((s) => !s)}
            className="relative p-2 rounded-lg hover:bg-surface-2 transition-colors"
          >
            <Bell size={16} className={unreadCount > 0 ? "text-primary" : "text-muted"} />
            {unreadCount > 0 && (
              <span className="absolute top-0.5 right-0.5 min-w-[14px] h-3.5 rounded-full bg-danger text-white text-[9px] font-bold flex items-center justify-center px-0.5">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {showAlerts && (
            <NotificationsPanel
              alerts={alerts}
              onClear={() => setAlerts([])}
              onClose={() => setShowAlerts(false)}
            />
          )}
        </div>
      </div>
    </header>
  );
}
