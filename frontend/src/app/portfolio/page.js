'use client';

import { useState, useEffect } from 'react';
import { PieChart, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import DataTable from '@/components/shared/DataTable';
import PctChange from '@/components/shared/PctChange';
import StrategyCard from '@/components/shared/StrategyCard';
import { formatCurrency, formatNumber } from '@/lib/utils';

const DEMO_PORTFOLIO_SUMMARY = {
  total_value: 245000,
  total_cost: 160000,
  total_pnl: 85000,
  total_pnl_pct: 53.1,
  cash: 85000,
  invested: 160000,
  allocation: { equities: 65, options: 10, bonds: 5, cash: 20 },
};

const DEMO_HOLDINGS = [
  { id: 1, ticker: 'NVDA', type: 'Stock', shares: 100, avg_price: 95.50, current: 142.30, market_value: 14230, pnl: 4680, pnl_pct: 49.0, allocation: 8.9 },
  { id: 2, ticker: 'NVDA250620C145', type: 'Call', shares: 3, avg_price: 3.20, current: 4.85, market_value: 1455, pnl: 495, pnl_pct: 51.6, allocation: 0.9 },
  { id: 3, ticker: 'AMD', type: 'Stock', shares: 200, avg_price: 110.00, current: 158.70, market_value: 31740, pnl: 9740, pnl_pct: 44.3, allocation: 12.9 },
  { id: 4, ticker: 'AMD250620C165', type: 'Call', shares: 5, avg_price: 8.50, current: 12.20, market_value: 6100, pnl: 1850, pnl_pct: 43.5, allocation: 2.5 },
  { id: 5, ticker: 'TSLA', type: 'Stock', shares: 50, avg_price: 220.00, current: 245.60, market_value: 12280, pnl: 1280, pnl_pct: 11.6, allocation: 5.0 },
  { id: 6, ticker: 'TSLA250718P220', type: 'Put', shares: -2, avg_price: 5.80, current: 3.20, market_value: 640, pnl: 520, pnl_pct: 44.8, allocation: 0.4 },
  { id: 7, ticker: 'AAPL', type: 'Stock', shares: 150, avg_price: 185.00, current: 199.80, market_value: 29970, pnl: 2220, pnl_pct: 8.0, allocation: 12.2 },
];

export default function PortfolioPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 400);
    return () => clearTimeout(t);
  }, []);

  const cols = [
    { key: 'ticker', label: 'Ticker' },
    { key: 'type', label: 'Type' },
    { key: 'shares', label: 'Qty', render: (v) => formatNumber(Math.abs(v)) },
    { key: 'avg_price', label: 'Avg Price', render: (v) => formatCurrency(v) },
    { key: 'current', label: 'Current', render: (v) => formatCurrency(v) },
    { key: 'market_value', label: 'Market Val', render: (v) => formatCurrency(v) },
    { key: 'pnl', label: 'P&L', render: (v) => <span className={v >= 0 ? 'text-terminal-green' : 'text-terminal-red'}>{formatCurrency(v)}</span> },
    { key: 'pnl_pct', label: 'P&L %', render: (v) => <PctChange value={v} /> },
    { key: 'allocation', label: 'Alloc', render: (v) => `${v.toFixed(1)}%` },
  ];

  if (loading) {
    return (
      <div className="animate-pulse space-y-6 max-w-7xl">
        <div className="h-8 bg-terminal-bg-card rounded w-48" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-terminal-bg-card rounded-xl" />)}
        </div>
        <div className="h-64 bg-terminal-bg-card rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-sans font-bold text-terminal-text">Portfolio</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StrategyCard title="Total Value" metrics={{}}>
          <p className="text-2xl font-mono font-bold text-terminal-green mt-2">{formatCurrency(DEMO_PORTFOLIO_SUMMARY.total_value)}</p>
        </StrategyCard>
        <StrategyCard title="Total P&L" metrics={{}}>
          <div className="flex items-center gap-2 mt-2">
            <TrendingUp size={20} className="text-terminal-green" />
            <p className="text-2xl font-mono font-bold text-terminal-green">{formatCurrency(DEMO_PORTFOLIO_SUMMARY.total_pnl)}</p>
          </div>
          <PctChange value={DEMO_PORTFOLIO_SUMMARY.total_pnl_pct} />
        </StrategyCard>
        <StrategyCard title="Cash" metrics={{}}>
          <p className="text-2xl font-mono font-bold text-terminal-text mt-2">{formatCurrency(DEMO_PORTFOLIO_SUMMARY.cash)}</p>
          <p className="text-xs font-mono text-terminal-text-muted">{DEMO_PORTFOLIO_SUMMARY.allocation.cash}% allocation</p>
        </StrategyCard>
        <StrategyCard title="Invested" metrics={{}}>
          <p className="text-2xl font-mono font-bold text-terminal-text mt-2">{formatCurrency(DEMO_PORTFOLIO_SUMMARY.invested)}</p>
          <p className="text-xs font-mono text-terminal-text-muted">{DEMO_PORTFOLIO_SUMMARY.allocation.equities + DEMO_PORTFOLIO_SUMMARY.allocation.options}% in market</p>
        </StrategyCard>
      </div>

      {/* Holdings Table */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <h2 className="text-base font-sans font-semibold text-terminal-text mb-4">Holdings</h2>
        <DataTable columns={cols} data={DEMO_HOLDINGS} />
      </div>
    </div>
  );
}
