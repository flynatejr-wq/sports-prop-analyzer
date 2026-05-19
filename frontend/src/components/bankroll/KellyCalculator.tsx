"use client";
import { useState } from "react";
import { getKellySizing } from "@/lib/api";
import type { KellyResponse } from "@/lib/types";
import { Calculator } from "lucide-react";

export default function KellyCalculator() {
  const [bankroll, setBankroll] = useState(1000);
  const [probWin, setProbWin] = useState(0.55);
  const [odds, setOdds] = useState(-110);
  const [fraction, setFraction] = useState(0.25);
  const [result, setResult] = useState<KellyResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function calculate() {
    setLoading(true);
    try {
      const res = await getKellySizing({
        bankroll,
        prob_win: probWin,
        american_odds: odds,
        fraction,
        max_pct: 0.05,
      });
      setResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-5">
        <Calculator size={16} className="text-primary" />
        <h3 className="text-white font-semibold">Kelly Criterion Calculator</h3>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <Field
          label="Bankroll ($)"
          value={bankroll}
          onChange={setBankroll}
          step={100}
          min={0}
        />
        <Field
          label="Win Probability"
          value={probWin}
          onChange={setProbWin}
          step={0.01}
          min={0.01}
          max={0.99}
        />
        <Field
          label="American Odds"
          value={odds}
          onChange={setOdds}
          step={5}
        />
        <div>
          <label className="text-xs text-muted block mb-1.5">Kelly Fraction</label>
          <div className="flex gap-1">
            {[0.25, 0.5, 1.0].map((f) => (
              <button
                key={f}
                onClick={() => setFraction(f)}
                className={`flex-1 py-2 rounded-lg text-xs font-medium transition-all border ${
                  fraction === f
                    ? "bg-primary text-white border-primary"
                    : "bg-surface-2 text-muted border-border hover:text-white"
                }`}
              >
                {f === 1 ? "Full" : f === 0.5 ? "Half" : "Quarter"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={calculate}
        disabled={loading}
        className="w-full py-2.5 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
      >
        {loading ? "Calculating..." : "Calculate Stake"}
      </button>

      {result && (
        <div className="mt-4 grid grid-cols-2 gap-3">
          <ResultTile
            label="Recommended Stake"
            value={`$${result.recommended_stake.toFixed(2)}`}
            highlight
          />
          <ResultTile
            label="Kelly Fraction"
            value={`${(result.kelly_fraction * 100).toFixed(2)}%`}
          />
          <ResultTile
            label="Expected Profit"
            value={`$${result.expected_profit.toFixed(2)}`}
            positive={result.expected_profit > 0}
          />
          <ResultTile
            label="Risk % of Bankroll"
            value={`${result.risk_pct.toFixed(2)}%`}
          />
        </div>
      )}
    </div>
  );
}

function Field({
  label, value, onChange, step = 1, min, max
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
}) {
  return (
    <div>
      <label className="text-xs text-muted block mb-1.5">{label}</label>
      <input
        type="number"
        value={value}
        step={step}
        min={min}
        max={max}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary"
      />
    </div>
  );
}

function ResultTile({
  label, value, highlight, positive
}: {
  label: string; value: string; highlight?: boolean; positive?: boolean;
}) {
  return (
    <div className="bg-surface-2 border border-border rounded-lg p-3">
      <p className="text-muted text-xs mb-1">{label}</p>
      <p className={`text-lg font-bold font-mono ${
        highlight ? "text-primary" :
        positive === true ? "text-success" :
        positive === false ? "text-danger" :
        "text-white"
      }`}>
        {value}
      </p>
    </div>
  );
}
