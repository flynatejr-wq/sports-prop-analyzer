"use client";
import { useState, useEffect } from "react";
import useSWR, { mutate as globalMutate } from "swr";
import { motion } from "framer-motion";
import { Bell, Wallet, Layout, Shield, TestTube2, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { FadeIn } from "@/components/ui/AnimatedCard";
import { useNotificationStore } from "@/store";

async function fetchSettings() {
  const res = await fetch(`/api/v1/settings/`);
  return res.json();
}

async function fetchStatus() {
  const res = await fetch(`/api/v1/settings/system-status`);
  return res.json();
}

function SectionHeader({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
  return (
    <div className="flex items-center gap-3 pb-4 border-b border-border">
      <div className="p-2 bg-primary/20 rounded-lg">
        <Icon size={16} className="text-primary" />
      </div>
      <div>
        <h2 className="text-white font-semibold text-sm">{title}</h2>
        <p className="text-muted text-xs">{description}</p>
      </div>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={clsx(
        "w-10 h-5 rounded-full transition-colors relative",
        checked ? "bg-primary" : "bg-surface-3"
      )}
    >
      <motion.div
        animate={{ x: checked ? 20 : 2 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
        className="absolute top-1 w-3 h-3 rounded-full bg-white"
      />
    </button>
  );
}

function StatusIndicator({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      {ok
        ? <CheckCircle size={14} className="text-success" />
        : <XCircle size={14} className="text-muted" />}
      <span className={clsx("text-xs", ok ? "text-success" : "text-muted")}>{label}</span>
    </div>
  );
}

export default function SettingsPage() {
  const { addToast } = useNotificationStore();
  const { data: settings, isLoading } = useSWR("settings", fetchSettings);
  const { data: status } = useSWR("system-status", fetchStatus, { refreshInterval: 10000 });

  const [saving, setSaving] = useState(false);
  const [testingDiscord, setTestingDiscord] = useState(false);
  const [testingTelegram, setTestingTelegram] = useState(false);

  // Local state mirrors fetched settings
  const [alertSettings, setAlertSettings] = useState({
    discord_enabled: true,
    telegram_enabled: false,
    sms_enabled: false,
    email_enabled: false,
    min_ev_threshold: 5.0,
    alert_on_injury: true,
    alert_on_steam: true,
    alert_on_stale_line: false,
  });

  const [bankrollSettings, setBankrollSettings] = useState({
    bankroll: 1000,
    unit_size: 10,
    kelly_fraction: 0.25,
    max_bet_pct: 5.0,
    risk_tolerance: "MEDIUM",
  });

  useEffect(() => {
    if (settings) {
      if (settings.alerts) setAlertSettings(settings.alerts);
      if (settings.bankroll) setBankrollSettings(settings.bankroll);
    }
  }, [settings]);

  async function saveAlerts() {
    setSaving(true);
    try {
      await fetch(`/api/v1/settings/alerts`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(alertSettings),
      });
      addToast({ type: "success", title: "Alert settings saved" });
    } catch {
      addToast({ type: "error", title: "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  }

  async function saveBankroll() {
    setSaving(true);
    try {
      await fetch(`/api/v1/settings/bankroll`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bankrollSettings),
      });
      addToast({ type: "success", title: "Bankroll settings saved" });
    } catch {
      addToast({ type: "error", title: "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  }

  async function testDiscord() {
    setTestingDiscord(true);
    try {
      const res = await fetch(`/api/v1/settings/test-discord`);
      const data = await res.json();
      addToast({ type: data.success ? "success" : "warning", title: data.message });
    } finally {
      setTestingDiscord(false);
    }
  }

  async function testTelegram() {
    setTestingTelegram(true);
    try {
      const res = await fetch(`/api/v1/settings/test-telegram`);
      const data = await res.json();
      addToast({ type: data.success ? "success" : "warning", title: data.success ? "Telegram test sent!" : "Telegram not configured" });
    } finally {
      setTestingTelegram(false);
    }
  }

  return (
    <FadeIn className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-muted text-sm mt-1">Configure alerts, bankroll, and display preferences</p>
      </div>

      {/* System Status */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <SectionHeader icon={Shield} title="System Status" description="Live feed of connected services" />
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-3">
          {status ? (
            <>
              <StatusIndicator ok={!!status.discord_configured} label="Discord" />
              <StatusIndicator ok={!!status.telegram_configured} label="Telegram" />
              <StatusIndicator ok={!!status.sms_configured} label="SMS (Twilio)" />
              <StatusIndicator ok={!!status.odds_api_configured} label="TheOddsAPI" />
              <StatusIndicator ok={status.active_props_cached > 0} label={`${status.active_props_cached} props cached`} />
              <StatusIndicator ok={!!status.last_refresh} label={status.last_refresh ? "Data refreshing" : "No refresh yet"} />
            </>
          ) : (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-5 w-24 bg-surface-2 rounded animate-pulse" />
            ))
          )}
        </div>
        {status?.last_refresh && (
          <p className="text-muted text-xs mt-3">
            Last refresh: {status.last_refresh.replace("T", " ").slice(0, 19)} UTC
          </p>
        )}
      </div>

      {/* Alerts */}
      <div className="bg-surface border border-border rounded-xl p-5 space-y-5">
        <SectionHeader icon={Bell} title="Alert Settings" description="Configure when and how you receive alerts" />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          {[
            { key: "discord_enabled", label: "Discord Alerts" },
            { key: "telegram_enabled", label: "Telegram Alerts" },
            { key: "sms_enabled", label: "SMS Alerts" },
            { key: "email_enabled", label: "Email Alerts" },
            { key: "alert_on_injury", label: "Injury News" },
            { key: "alert_on_steam", label: "Steam Moves" },
            { key: "alert_on_stale_line", label: "Stale Lines" },
          ].map(({ key, label }) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm text-white">{label}</span>
              <Toggle
                checked={alertSettings[key as keyof typeof alertSettings] as boolean}
                onChange={(v) => setAlertSettings((s) => ({ ...s, [key]: v }))}
              />
            </div>
          ))}
        </div>

        <div>
          <label className="text-xs text-muted block mb-1.5">Minimum EV% to Alert</label>
          <div className="flex items-center gap-3">
            <input
              type="range" min={0} max={20} step={0.5}
              value={alertSettings.min_ev_threshold}
              onChange={(e) => setAlertSettings((s) => ({ ...s, min_ev_threshold: parseFloat(e.target.value) }))}
              className="flex-1 accent-primary"
            />
            <span className="text-white font-mono text-sm w-12 text-right">
              {alertSettings.min_ev_threshold}%
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2 border-t border-border">
          <button
            onClick={testDiscord}
            disabled={testingDiscord}
            className="flex items-center gap-2 px-3 py-2 bg-surface-2 border border-border rounded-lg text-xs text-muted hover:text-white transition-colors disabled:opacity-50"
          >
            {testingDiscord ? <Loader2 size={12} className="animate-spin" /> : <TestTube2 size={12} />}
            Test Discord
          </button>
          <button
            onClick={testTelegram}
            disabled={testingTelegram}
            className="flex items-center gap-2 px-3 py-2 bg-surface-2 border border-border rounded-lg text-xs text-muted hover:text-white transition-colors disabled:opacity-50"
          >
            {testingTelegram ? <Loader2 size={12} className="animate-spin" /> : <TestTube2 size={12} />}
            Test Telegram
          </button>
          <button
            onClick={saveAlerts}
            disabled={saving}
            className="ml-auto px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Alerts"}
          </button>
        </div>
      </div>

      {/* Bankroll */}
      <div className="bg-surface border border-border rounded-xl p-5 space-y-4">
        <SectionHeader icon={Wallet} title="Bankroll Settings" description="Manage your betting bankroll and unit sizing" />

        <div className="grid grid-cols-2 gap-4 mt-4">
          {[
            { key: "bankroll", label: "Bankroll ($)", step: 100 },
            { key: "unit_size", label: "Unit Size ($)", step: 5 },
            { key: "max_bet_pct", label: "Max Bet %", step: 0.5 },
          ].map(({ key, label, step }) => (
            <div key={key}>
              <label className="text-xs text-muted block mb-1.5">{label}</label>
              <input
                type="number"
                step={step}
                min={0}
                value={bankrollSettings[key as keyof typeof bankrollSettings] as number}
                onChange={(e) =>
                  setBankrollSettings((s) => ({
                    ...s,
                    [key]: parseFloat(e.target.value) || 0,
                  }))
                }
                className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary"
              />
            </div>
          ))}

          <div>
            <label className="text-xs text-muted block mb-1.5">Kelly Fraction</label>
            <div className="flex gap-1">
              {[0.25, 0.5, 1.0].map((f) => (
                <button
                  key={f}
                  onClick={() => setBankrollSettings((s) => ({ ...s, kelly_fraction: f }))}
                  className={clsx(
                    "flex-1 py-2 rounded-lg text-xs font-medium transition-all border",
                    bankrollSettings.kelly_fraction === f
                      ? "bg-primary text-white border-primary"
                      : "bg-surface-2 text-muted border-border hover:text-white"
                  )}
                >
                  {f === 1 ? "Full" : f === 0.5 ? "Half" : "¼"}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-muted block mb-1.5">Risk Tolerance</label>
            <div className="flex gap-1">
              {["LOW", "MEDIUM", "HIGH"].map((r) => (
                <button
                  key={r}
                  onClick={() => setBankrollSettings((s) => ({ ...s, risk_tolerance: r }))}
                  className={clsx(
                    "flex-1 py-2 rounded-lg text-xs font-medium transition-all border",
                    bankrollSettings.risk_tolerance === r
                      ? r === "LOW" ? "bg-success/20 text-success border-success/40"
                        : r === "HIGH" ? "bg-danger/20 text-danger border-danger/40"
                        : "bg-warning/20 text-warning border-warning/40"
                      : "bg-surface-2 text-muted border-border hover:text-white"
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-2 border-t border-border">
          <button
            onClick={saveBankroll}
            disabled={saving}
            className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Bankroll"}
          </button>
        </div>
      </div>

      {/* .env reminder */}
      <div className="bg-surface-2 border border-border rounded-xl p-4">
        <p className="text-xs text-muted">
          <span className="text-white font-medium">API Keys & Webhooks</span> are configured via your{" "}
          <code className="bg-surface-3 px-1 py-0.5 rounded text-primary">.env</code> file.
          Restart the backend after changes. See{" "}
          <code className="bg-surface-3 px-1 py-0.5 rounded text-primary">.env.example</code> for all options.
        </p>
      </div>
    </FadeIn>
  );
}
