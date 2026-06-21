'use client';

import { useState, useEffect } from 'react';
import { Activity, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import StatusDot from '@/components/shared/StatusDot';
import PctChange from '@/components/shared/PctChange';
import DataTable from '@/components/shared/DataTable';
import StrategyCard from '@/components/shared/StrategyCard';

const DEMO_SERVICES = [
  { id: 1, name: 'Market Data Feed', status: 'online', uptime: '99.97%', last_check: '2s ago', latency: '12ms' },
  { id: 2, name: 'Trading Engine', status: 'online', uptime: '99.94%', last_check: '1s ago', latency: '8ms' },
  { id: 3, name: 'Risk Monitor', status: 'online', uptime: '99.99%', last_check: '3s ago', latency: '5ms' },
  { id: 4, name: 'Portfolio API', status: 'online', uptime: '99.88%', last_check: '5s ago', latency: '15ms' },
  { id: 5, name: 'Database', status: 'online', uptime: '99.99%', last_check: '1s ago', latency: '3ms' },
  { id: 6, name: 'AI Analysis Engine', status: 'online', uptime: '99.76%', last_check: '10s ago', latency: '45ms' },
];

const DEMO_ALERTS = [
  { id: 1, severity: 'info', message: 'NVDA approaching target price', time: '5m ago', category: 'price' },
  { id: 2, severity: 'warning', message: 'Portfolio concentration in semis exceeds 40%', time: '15m ago', category: 'risk' },
  { id: 3, severity: 'info', message: 'TSLA CSP IV contraction — 30% drop', time: '1h ago', category: 'options' },
  { id: 4, severity: 'success', message: 'AMD LEAPS Delta 0.75 — deep ITM', time: '2h ago', category: 'options' },
  { id: 5, severity: 'warning', message: 'Cash drag: 20% allocation earning 0%', time: '4h ago', category: 'portfolio' },
  { id: 6, severity: 'info', message: 'CPI data scheduled next week', time: '6h ago', category: 'macro' },
];

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

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 400);
    return () => clearTimeout(t);
  }, []);

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

  const svcCols = [
    { key: 'name', label: 'Service' },
    { key: 'status', label: 'Status', render: (v) => <StatusDot status={v} label={v === 'online' ? 'Online' : 'Offline'} /> },
    { key: 'uptime', label: 'Uptime' },
    { key: 'latency', label: 'Latency' },
    { key: 'last_check', label: 'Last Check' },
  ];

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-sans font-bold text-terminal-text">Monitoring</h1>
        <StatusDot status="online" label="All Systems Operational" />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StrategyCard title="Services" metrics={{ Online: '6 / 6', Uptime: '99.92%', Latency: '14ms avg' }} />
        <StrategyCard title="Active Alerts" metrics={{ Warnings: '2', Info: '4', Critical: '0' }} />
        <StrategyCard title="System" metrics={{ Uptime: '14d 6h 32m', Version: '2.4.1', 'Last Deploy': '2d ago' }} />
      </div>

      {/* Services Table */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <h2 className="text-base font-sans font-semibold text-terminal-text mb-4">Services</h2>
        <DataTable columns={svcCols} data={DEMO_SERVICES} />
      </div>

      {/* Alerts */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-sans font-semibold text-terminal-text">Recent Alerts</h2>
          <span className="text-xs font-mono text-terminal-text-muted">Last 6 alerts</span>
        </div>
        <div className="space-y-2">
          {DEMO_ALERTS.map((a) => (
            <div key={a.id} className={`flex items-start gap-3 p-3 rounded-lg bg-terminal-bg-light border-l-2 ${sevBg(a.severity)}`}>
              {sevIcon(a.severity)}
              <div className="flex-1">
                <p className="text-sm font-sans text-terminal-text">{a.message}</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs font-mono text-terminal-text-muted uppercase">{a.category}</span>
                  <span className="text-xs font-mono text-terminal-text-muted flex items-center gap-1"><Clock size={12} />{a.time}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
