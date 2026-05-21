"use client";
import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  Menu, X, BarChart3, Target, TrendingUp, Wallet, Activity,
  LineChart, Settings, Play, Users, Wifi,
} from "lucide-react";
import { clsx } from "clsx";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";

// ── Bottom nav items (mobile only) ────────────────────────────────────────────
const BOTTOM_NAV = [
  { href: "/",            icon: BarChart3, label: "Home"    },
  { href: "/props",       icon: Target,    label: "Props"   },
  { href: "/quick-picks", icon: Play,      label: "Quick"   },
  { href: "/live-props",  icon: Wifi,      label: "Live"    },
  { href: "/analytics",   icon: TrendingUp,label: "Stats"   },
];

function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-surface border-t border-border z-40 flex md:hidden">
      {BOTTOM_NAV.map(({ href, icon: Icon, label }) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors",
              isActive ? "text-primary" : "text-muted hover:text-white"
            )}
          >
            <Icon size={18} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

// ── Main layout ───────────────────────────────────────────────────────────────

export default function MobileAwareLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Close sidebar on route change
  const pathname = usePathname();
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  // Close sidebar on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSidebarOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  return (
    <div className="flex min-h-screen">
      {/* ── Desktop sidebar (hidden on mobile) ──────────────────────────────── */}
      <div className="hidden md:block flex-shrink-0">
        <Sidebar />
      </div>

      {/* ── Mobile sidebar overlay ──────────────────────────────────────────── */}
      {sidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 z-40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          {/* Sidebar drawer */}
          <div className="fixed left-0 top-0 bottom-0 w-64 z-50 md:hidden shadow-2xl">
            <Sidebar />
            <button
              onClick={() => setSidebarOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg bg-surface-2 text-muted hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </>
      )}

      {/* ── Main content ────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        {/* Navbar — with mobile menu button */}
        <div className="relative">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 md:hidden z-10">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-surface-2 transition-colors"
            >
              <Menu size={18} className="text-muted" />
            </button>
          </div>
          <div className="md:pl-0 pl-12">
            <Navbar />
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1 p-4 md:p-6 overflow-auto pb-20 md:pb-6">
          {children}
        </main>
      </div>

      {/* ── Mobile bottom nav ────────────────────────────────────────────────── */}
      <BottomNav />
    </div>
  );
}
