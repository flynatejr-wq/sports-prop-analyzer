"use client";
import { useState } from "react";
import { Search, RefreshCw, Bell } from "lucide-react";
import { triggerRefresh, searchPlayerProps } from "@/lib/api";
import type { Prop } from "@/lib/types";

export default function Navbar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Prop[]>([]);
  const [searching, setSearching] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

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
    setRefreshing(true);
    try {
      await triggerRefresh();
    } finally {
      setTimeout(() => setRefreshing(false), 2000);
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
        {/* Search dropdown */}
        {results.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-surface-2 border border-border rounded-lg shadow-xl z-50 overflow-hidden">
            {results.map((p) => (
              <a
                key={p.id}
                href={`/props/${p.id}`}
                className="flex items-center justify-between px-4 py-2.5 hover:bg-surface-3 transition-colors"
                onClick={() => { setResults([]); setQuery(""); }}
              >
                <div>
                  <p className="text-white text-sm font-medium">{p.player_name}</p>
                  <p className="text-muted text-xs">{p.sport} • {p.stat_type}</p>
                </div>
                <span className="text-xs font-mono text-primary">{p.line}</span>
              </a>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 ml-auto">
        {/* Refresh */}
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 bg-surface-2 border border-border rounded-lg text-sm text-muted hover:text-white hover:border-primary transition-all disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-surface-2 transition-colors">
          <Bell size={16} className="text-muted" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-danger" />
        </button>
      </div>
    </header>
  );
}
