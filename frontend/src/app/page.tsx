import StatsOverview from "@/components/dashboard/StatsOverview";
import TopPicks from "@/components/dashboard/TopPicks";
import LiveFeed from "@/components/dashboard/LiveFeed";
import EVChart from "@/components/charts/EVChart";

// Server component — initial data via API, then SWR takes over on client
async function getInitialProps() {
  try {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const res = await fetch(`${base}/api/v1/props/best-bets`, {
      next: { revalidate: 30 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function DashboardPage() {
  const initialProps = await getInitialProps();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-muted text-sm mt-1">Real-time prop analysis • Auto-refreshes every 30s</p>
      </div>

      {/* KPI tiles */}
      <StatsOverview />

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Props + chart — takes 3 cols */}
        <div className="xl:col-span-3 space-y-6">
          {initialProps.length > 0 && <EVChart props={initialProps} />}
          <TopPicks />
        </div>

        {/* Live sidebar — 1 col */}
        <div className="space-y-4">
          <LiveFeed />
          <div className="bg-surface border border-border rounded-xl p-4">
            <h3 className="text-white font-semibold text-sm mb-3">Quick Stats</h3>
            <div className="space-y-2">
              {[
                { label: "Data refresh", value: "Every 30s" },
                { label: "Sports covered", value: "NBA, NFL, MLB, NHL" },
                { label: "Alert threshold", value: "EV > 5%" },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center text-xs">
                  <span className="text-muted">{label}</span>
                  <span className="text-white font-medium">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
