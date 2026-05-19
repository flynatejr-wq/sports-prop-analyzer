"use client";
import KellyCalculator from "@/components/bankroll/KellyCalculator";
import { Wallet } from "lucide-react";

export default function BankrollPage() {
  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      <div>
        <div className="flex items-center gap-2">
          <Wallet size={20} className="text-primary" />
          <h1 className="text-2xl font-bold text-white">Bankroll Manager</h1>
        </div>
        <p className="text-muted text-sm mt-1">
          Kelly Criterion sizing, ROI tracking, and stake recommendations
        </p>
      </div>

      <KellyCalculator />

      {/* Kelly reference card */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="text-white font-semibold text-sm mb-3">Kelly Criterion Reference</h3>
        <div className="space-y-3 text-sm">
          <p className="text-muted">
            <span className="text-white font-medium">Full Kelly</span> — theoretically maximizes
            long-run growth but produces large swings. Use with care.
          </p>
          <p className="text-muted">
            <span className="text-white font-medium">Quarter Kelly (25%)</span> — recommended default.
            Reduces variance by 75% while capturing ~75% of the growth rate.
          </p>
          <p className="text-muted">
            <span className="text-white font-medium">Half Kelly (50%)</span> — moderate approach,
            good balance of growth and drawdown control.
          </p>
          <div className="mt-4 p-3 bg-surface-2 rounded-lg border border-border">
            <p className="text-xs text-muted font-mono">
              f* = (b·p - q) / b
            </p>
            <p className="text-xs text-muted mt-1">
              where b = net decimal odds, p = win probability, q = 1 - p
            </p>
          </div>
        </div>
      </div>

      {/* PrizePicks payout table */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="text-white font-semibold text-sm mb-3">PrizePicks Payout Table</h3>
        <div className="grid grid-cols-5 gap-2">
          {[
            { legs: 2, payout: "3x", breakeven: "57.7%" },
            { legs: 3, payout: "5x", breakeven: "58.5%" },
            { legs: 4, payout: "10x", breakeven: "56.2%" },
            { legs: 5, payout: "20x", breakeven: "55.0%" },
            { legs: 6, payout: "40x", breakeven: "54.2%" },
          ].map(({ legs, payout, breakeven }) => (
            <div key={legs} className="bg-surface-2 rounded-lg p-3 text-center">
              <p className="text-muted text-xs">{legs}-Leg</p>
              <p className="text-white font-bold text-lg">{payout}</p>
              <p className="text-muted text-[10px] mt-1">B/E: {breakeven}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
