"use client";
import { Suspense } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  BarChart3, Zap, Target, TrendingUp, Wallet, AlertCircle,
  Activity, ChevronRight, Flame, Shield, Wifi, LineChart, Settings, Users
} from "lucide-react";
import { clsx } from "clsx";

const nav = [
  { href: "/", label: "Dashboard", icon: BarChart3, section: null },
  { href: "/props", label: "All Props", icon: Target, section: "Props" },
  { href: "/props?tab=best-bets", label: "Best Bets", icon: Flame, section: "Props" },
  { href: "/props?tab=mispriced", label: "Mispriced", icon: AlertCircle, section: "Props" },
  { href: "/props?tab=sharp", label: "Sharp Action", icon: Shield, section: "Props" },
  { href: "/props?tab=parlay", label: "Parlay Builder", icon: Zap, section: "Props" },
  { href: "/live-props", label: "Live Props", icon: Wifi, section: "Live" },
  { href: "/line-movement", label: "Line Movement", icon: LineChart, section: "Live" },
  { href: "/players", label: "Players", icon: Users, section: "Live" },
  { href: "/analytics", label: "Analytics", icon: TrendingUp, section: "Tools" },
  { href: "/bankroll", label: "Bankroll", icon: Wallet, section: "Tools" },
  { href: "/settings", label: "Settings", icon: Settings, section: "Tools" },
];

const SECTIONS = ["Props", "Live", "Tools"];

function NavLink({ href, label, icon: Icon }: { href: string; label: string; icon: React.ElementType }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [path, query] = href.split("?");
  const currentFull = pathname + (searchParams.toString() ? `?${searchParams.toString()}` : "");
  const isActive = query
    ? currentFull === href
    : pathname === path;

  return (
    <Link href={href} className={clsx(
      "flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
      isActive ? "bg-primary text-white shadow-lg shadow-primary/20" : "text-muted hover:text-white hover:bg-surface-2"
    )}>
      <div className="flex items-center gap-3"><Icon size={16} />{label}</div>
      {isActive && <ChevronRight size={14} />}
    </Link>
  );
}

function NavTree() {
  return (
    <nav className="flex-1 px-3 py-4 space-y-4 overflow-y-auto">
      {nav.filter(n => !n.section).map((item) => (
        <NavLink key={item.href} {...item} icon={item.icon} />
      ))}
      {SECTIONS.map((section) => {
        const items = nav.filter(n => n.section === section);
        return (
          <div key={section}>
            <p className="text-[10px] font-semibold text-muted/60 uppercase tracking-widest px-3 mb-1">{section}</p>
            <div className="space-y-0.5">
              {items.map((item) => (
                <NavLink key={item.href} {...item} icon={item.icon} />
              ))}
            </div>
          </div>
        );
      })}
    </nav>
  );
}

export default function Sidebar() {
  return (
    <aside className="w-64 min-h-screen bg-surface border-r border-border flex flex-col">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Activity size={18} className="text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-tight">PropEdge</p>
            <p className="text-muted text-xs">AI Prop Intelligence</p>
          </div>
        </div>
      </div>

      <Suspense fallback={<nav className="flex-1" />}>
        <NavTree />

      </Suspense>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-border">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span className="text-xs text-muted">Live data active</span>
        </div>
      </div>
    </aside>
  );
}
