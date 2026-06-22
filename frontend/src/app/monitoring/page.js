'use client';

import { useState, useEffect } from 'react';
import { Activity, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import StatusDot from '@/components/shared/StatusDot';
import PctChange from '@/components/shared/PctChange';
import DataTable from '@/components/shared/DataTable';
import StrategyCard from '@/components/shared/StrategyCard';
import { getMonitoringSummary, getMonitoringAlerts } from '@/lib/api';

const sevIcon = (sev) => {
  switch (sev) {
    case 'warning': return <AlertTriangle size={16} className="text-terminal-yellow" />;
    case 'success': return <CheckCircle size={16} className="text-terminal-green" />;
    default: return <Activity size={16} className="text-terminal-blue" />;
  }
};

const sevBg = (sev) => {
  switch (sev) {
    case 'warning': return 'border-l-terminal-yellow';
    case 'success': return 'border-l-terminal-green';
    default: return 'border-l-terminal-blue';
  }
};

export default function MonitoringPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, alertsData] = await Promise.allSettled([
        getMonitoringSummary(),
        getMonitoringAlerts(),
      ]);
      if (summaryData.status === 'fulfilled') setSummary(summaryData.value);
      if (alertsData.status === 'fulfilled') setAlerts(Array.isArray(alertsData.value) ? alertsData.value : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) {
    return (
      <div className="animate-pulse space-y-6 max-w-7xl">
        <div className="h-8 bg-terminal-bg-card rounded w-48" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <div key={i} className="h-24 bg-terminal-bg-card rounded-xl" />)}
        </div>
        <div className="h-64 bg-terminal-bg-card rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-terminal-red/10 border border-terminal-red/30 rounded-xl p-5 flex items-center justify-between max-w-7xl">
        <p className="text-sm font-mono text-terminal-red">{error}</p>
        <button onClick={fetchData} className="text-sm font-mono text-terminal-red hover:text-terminal-text transition-colors">Retry</button>
      </div>
    );
  }

  const positions = summary?.positions || [];
  const openOrders = summary?.open_orders || [];
  const health = summary?.health;
  const portfolio = summary?.portfolio;

  const positionsForTable = positions.map((p) => ({
    ...p,
    id: p.ticker,
  }));

  const svcCols = [
    { key: 'ticker', label: 'Ticker' },
    { key: 'quantity', label: 'Quantity', render: (v) => Math.abs(v) },
    { key: 'market_value', label: 'Market Value', render: (v) => `$${(v || 0).toFixed(2)}` },
    { key: 'unrealized_pl', label: 'P&L', render: (v) => <span className={(v || 0) >= 0 ? 'text-terminal-green' : 'text-terminal-red'}>${Math.abs(v || 0).toFixed(2)}</span> },
    { key: 'strategy_type', label: 'Strategy' },
    { key: 'sector', label: 'Sector' },
  ];

  const healthScore = health?.score ?? 0;
  const onlineCount = positions.length > 0 ? positions.length : 0;

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-sans font-bold text-terminal-text">Monitoring</h1>
        <StatusDot status="online" label="All Systems Operational" />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StrategyCard title="Portfolio" metrics={{
          Value: portfolio?.total_value ? `$${portfolio.total_value.toFixed(2)}` : '$0.00',
          Positions: String(positions.length),
          Orders: String(openOrders.length),
        }} />
        <StrategyCard title="Health" metrics={{
          Score: String(healthScore),
          Level: health?.level || 'N/A',
        }} />
        <StrategyCard title="System" metrics={{
          Beta: portfolio?.portfolio_beta?.toFixed(2) ?? '-',
          Delta: portfolio?.portfolio_delta_e?.toFixed(2) ?? '-',
        }} />
      </div>

      {/* Positions Table */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <h2 className="text-base font-sans font-semibold text-terminal-text mb-4">Positions</h2>
        {positionsForTable.length === 0 ? (
          <p className="text-sm text-terminal-text-muted font-mono">No positions found</p>
        ) : (
          <DataTable columns={svcCols} data={positionsForTable} />
        )}
      </div>

      {/* Alerts */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-sans font-semibold text-terminal-text">Recent Alerts</h2>
          <span className="text-xs font-mono text-terminal-text-muted">Last {alerts.length} alerts</span>
        </div>
        <div className="space-y-2">
          {alerts.length === 0 && (
            <p className="text-sm text-terminal-text-muted font-mono">No alerts</p>
          )}
          {alerts.map((a, i) => (
            <div key={i} className={`flex items-start gap-3 p-3 rounded-lg bg-terminal-bg-light border-l-2 ${sevBg(a.severity)}`}>
              {sevIcon(a.severity)}
              <div className="flex-1">
                <p className="text-sm font-sans text-terminal-text">{a.message}</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs font-mono text-terminal-text-muted uppercase">{a.alert_type || a.category || 'system'}</span>
                  {a.timestamp && (
                    <span className="text-xs font-mono text-terminal-text-muted flex items-center gap-1"><Clock size={12} />{new Date(a.timestamp).toLocaleTimeString()}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
