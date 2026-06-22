'use client';

import { useState, useEffect } from 'react';
import { PieChart, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import DataTable from '@/components/shared/DataTable';
import PctChange from '@/components/shared/PctChange';
import StrategyCard from '@/components/shared/StrategyCard';
import { formatCurrency, formatNumber } from '@/lib/utils';
import { getPortfolioSummary, getPortfolioHoldings } from '@/lib/api';
import { useTickerDetails } from '@/hooks/useTickerDetails';

export default function PortfolioPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [holdings, setHoldings] = useState([]);

  const tickers = holdings.map((h) => h.ticker);
  const { details } = useTickerDetails(tickers);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, holdingsData] = await Promise.allSettled([
        getPortfolioSummary(),
        getPortfolioHoldings(),
      ]);
      if (summaryData.status === 'fulfilled') setSummary(summaryData.value);
      if (holdingsData.status === 'fulfilled') setHoldings(holdingsData.value || []);
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-terminal-bg-card rounded-xl" />)}
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

  const totalValue = summary?.total_value ?? 0;
  const cash = summary?.cash ?? 0;
  const invested = totalValue - cash;
  const totalPnl = holdings.reduce((sum, h) => sum + (h.unrealized_pl || 0), 0);
  const totalPnlPct = totalValue > 0 ? (totalPnl / (totalValue - cash)) * 100 : 0;

  const cols = [
    { key: 'ticker', label: 'Ticker', render: (v) => {
      const info = details[v] || {};
      return (
        <div>
          <span className="font-mono font-semibold">{v}</span>
          {info.name && <p className="text-xs font-sans text-terminal-text-muted truncate max-w-[140px]">{info.name}</p>}
        </div>
      );
    }},
    { key: 'strategy_type', label: 'Type' },
    { key: 'quantity', label: 'Qty', render: (v) => formatNumber(Math.abs(v)) },
    { key: 'avg_price', label: 'Avg Price', render: (v) => formatCurrency(v) },
    { key: 'current_price', label: 'Current', render: (v) => formatCurrency(v) },
    { key: 'market_value', label: 'Market Val', render: (v) => formatCurrency(v) },
    { key: 'unrealized_pl', label: 'P&L', render: (v) => <span className={v >= 0 ? 'text-terminal-green' : 'text-terminal-red'}>{formatCurrency(v)}</span> },
    { key: 'unrealized_pl_pct', label: 'P&L %', render: (v) => <PctChange value={v} /> },
    { key: 'weight_pct', label: 'Alloc', render: (v) => `${(v || 0).toFixed(1)}%` },
  ];

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-sans font-bold text-terminal-text">Portfolio</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StrategyCard title="Total Value" metrics={{}}>
          <p className="text-2xl font-mono font-bold text-terminal-green mt-2">{formatCurrency(totalValue)}</p>
        </StrategyCard>
        <StrategyCard title="Total P&L" metrics={{}}>
          <div className="flex items-center gap-2 mt-2">
            {totalPnl >= 0 ? <TrendingUp size={20} className="text-terminal-green" /> : <TrendingDown size={20} className="text-terminal-red" />}
            <p className={`text-2xl font-mono font-bold ${totalPnl >= 0 ? 'text-terminal-green' : 'text-terminal-red'}`}>{formatCurrency(totalPnl)}</p>
          </div>
          <PctChange value={totalPnlPct} />
        </StrategyCard>
        <StrategyCard title="Cash" metrics={{}}>
          <p className="text-2xl font-mono font-bold text-terminal-text mt-2">{formatCurrency(cash)}</p>
          <p className="text-xs font-mono text-terminal-text-muted">{totalValue > 0 ? ((cash / totalValue) * 100).toFixed(1) : 0}% allocation</p>
        </StrategyCard>
        <StrategyCard title="Invested" metrics={{}}>
          <p className="text-2xl font-mono font-bold text-terminal-text mt-2">{formatCurrency(invested)}</p>
          <p className="text-xs font-mono text-terminal-text-muted">{summary?.num_positions ?? 0} positions</p>
        </StrategyCard>
      </div>

      {/* Holdings Table */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <h2 className="text-base font-sans font-semibold text-terminal-text mb-4">Holdings</h2>
        {holdings.length === 0 ? (
          <p className="text-sm text-terminal-text-muted font-mono">No holdings found</p>
        ) : (
          <DataTable columns={cols} data={holdings} />
        )}
      </div>
    </div>
  );
}
