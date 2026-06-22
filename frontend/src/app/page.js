'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, FileText, AlertTriangle } from 'lucide-react';
import RegimeDot from '@/components/shared/RegimeDot';
import PctChange from '@/components/shared/PctChange';
import ScoreBadge from '@/components/shared/ScoreBadge';
import DataTable from '@/components/shared/DataTable';
import StrategyCard from '@/components/shared/StrategyCard';
import { formatCurrency, formatNumber } from '@/lib/utils';
import { getRegime, getPortfolioHealth, getOpportunities, getPortfolioHoldings, getDailyReport } from '@/lib/api';
import { useTickerDetails } from '@/hooks/useTickerDetails';

function HealthGauge({ score }) {
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#eab308' : '#ef4444';
  const r = 44, circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;

  return (
    <div className="flex flex-col items-center">
      <svg width="120" height="120" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#2a2a2a" strokeWidth="8" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round" transform="rotate(-90 50 50)" style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
        <text x="50" y="48" textAnchor="middle" fill={color} fontSize="20" fontWeight="bold" fontFamily="IBM Plex Mono, monospace">{score}</text>
        <text x="50" y="64" textAnchor="middle" fill="#888" fontSize="8" fontFamily="IBM Plex Sans, sans-serif">/ 100</text>
      </svg>
      <p className="text-sm font-mono text-terminal-text-muted mt-1">Health Score</p>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-16 bg-terminal-bg-card rounded-xl" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="h-64 bg-terminal-bg-card rounded-xl" />
        <div className="lg:col-span-2 h-64 bg-terminal-bg-card rounded-xl" />
      </div>
      <div className="h-48 bg-terminal-bg-card rounded-xl" />
      <div className="h-48 bg-terminal-bg-card rounded-xl" />
    </div>
  );
}

function ErrorBanner({ message, onRetry }) {
  return (
    <div className="bg-terminal-red/10 border border-terminal-red/30 rounded-xl p-5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <AlertTriangle size={20} className="text-terminal-red" />
        <p className="text-sm font-mono text-terminal-red">{message}</p>
      </div>
      <button onClick={onRetry} className="text-sm font-mono text-terminal-red hover:text-terminal-text transition-colors">Retry</button>
    </div>
  );
}

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [regime, setRegime] = useState(null);
  const [health, setHealth] = useState(null);
  const [opps, setOpps] = useState([]);
  const [holdings, setHoldings] = useState([]);
  const [report, setReport] = useState(null);

  const allTickers = [...new Set([...opps.map((o) => o.ticker), ...holdings.map((h) => h.ticker)])];
  const { details } = useTickerDetails(allTickers);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [regimeData, healthData, oppsData, holdingsData, reportData] = await Promise.allSettled([
        getRegime(),
        getPortfolioHealth(),
        getOpportunities('all', 5),
        getPortfolioHoldings(),
        getDailyReport(),
      ]);
      if (regimeData.status === 'fulfilled') setRegime(regimeData.value);
      if (healthData.status === 'fulfilled') setHealth(healthData.value);
      if (oppsData.status === 'fulfilled') setOpps(oppsData.value.opportunities || []);
      if (holdingsData.status === 'fulfilled') setHoldings(holdingsData.value || []);
      if (reportData.status === 'fulfilled') setReport(reportData.value);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) return <LoadingSkeleton />;

  if (error) return <ErrorBanner message={error} onRetry={fetchData} />;

  const regimeLabel = regime?.overall_regime || 'Unknown';
  const healthScore = health?.portfolio_health_score ?? 0;
  const totalValue = health?.total_value ?? 0;
  const concentration = health?.concentration_pct ?? 0;

  const posCols = [
    { key: 'ticker', label: 'Ticker', render: (v) => {
      const info = details[v] || {};
      return (
        <div>
          <span className="font-mono font-semibold">{v}</span>
          {info.name && <p className="text-xs font-sans text-terminal-text-muted truncate max-w-[140px]">{info.name}</p>}
        </div>
      );
    }},
    { key: 'quantity', label: 'Shares', render: (v) => formatNumber(Math.abs(v)) },
    { key: 'avg_price', label: 'Avg Price', render: (v) => formatCurrency(v) },
    { key: 'current_price', label: 'Current', render: (v) => formatCurrency(v) },
    { key: 'unrealized_pl', label: 'P&L', render: (v) => <span className={v >= 0 ? 'text-terminal-green' : 'text-terminal-red'}>{formatCurrency(v)}</span> },
    { key: 'unrealized_pl_pct', label: 'P&L %', render: (v) => <PctChange value={v} /> },
  ];

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-sans font-bold text-terminal-text">Dashboard</h1>
        <p className="text-xs font-mono text-terminal-text-muted">Last updated: just now</p>
      </div>

      {/* Regime Banner */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {regimeLabel === 'bull' ? (
            <TrendingUp size={28} className="text-terminal-green" />
          ) : regimeLabel === 'bear' ? (
            <TrendingDown size={28} className="text-terminal-red" />
          ) : (
            <Activity size={28} className="text-terminal-yellow" />
          )}
          <div>
            <RegimeDot regime={regimeLabel} />
            <p className="text-sm text-terminal-text-muted font-sans mt-1">{regime?.ticker || 'SPY'} — {regimeLabel} market regime</p>
          </div>
        </div>
      </div>

      {/* Health + Top Opportunities */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <StrategyCard title="Portfolio Health" score={healthScore} className="flex flex-col items-center">
          <div className="mt-2">
            <HealthGauge score={healthScore} />
          </div>
          <div className="w-full mt-4 space-y-2 border-t border-terminal-border pt-4">
            <div className="flex justify-between text-sm font-mono">
              <span className="text-terminal-text-muted">Total Value</span>
              <span className="text-terminal-text">{formatCurrency(totalValue)}</span>
            </div>
            <div className="flex justify-between text-sm font-mono">
              <span className="text-terminal-text-muted">Concentration</span>
              <span className="text-terminal-text">{concentration.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between text-sm font-mono">
              <span className="text-terminal-text-muted">Beta</span>
              <span className="text-terminal-text">{health?.portfolio_beta?.toFixed(2) ?? '-'}</span>
            </div>
            <div className="flex justify-between text-sm font-mono">
              <span className="text-terminal-text-muted">Exposure</span>
              <span className="text-terminal-text">{health?.current_exposure ? formatCurrency(health.current_exposure) : '-'}</span>
            </div>
          </div>
        </StrategyCard>

        <div className="lg:col-span-2 bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-sans font-semibold text-terminal-text">Top Opportunities</h2>
            <span className="text-xs font-mono text-terminal-text-muted">Score weighted</span>
          </div>
          <div className="space-y-3">
            {opps.length === 0 && (
              <p className="text-sm text-terminal-text-muted font-mono">No opportunities computed yet</p>
            )}
            {opps.slice(0, 5).map((opp, i) => {
              const info = details[opp.ticker] || {};
              return (
              <div key={opp.ticker + i} className="flex items-center justify-between p-3 rounded-lg bg-terminal-bg-light hover:bg-terminal-bg-hover transition-colors">
                <div className="flex items-center gap-4">
                  <div>
                    <span className="font-mono font-semibold text-terminal-text">{opp.ticker}</span>
                    {info.name && <p className="text-xs font-sans text-terminal-text-muted truncate max-w-[180px]">{info.name}</p>}
                  </div>
                  <span className="px-2 py-0.5 text-xs font-mono rounded bg-terminal-green/10 text-terminal-green border border-terminal-green/20 uppercase tracking-wider">{opp.strategy_type}</span>
                </div>
                <div className="flex items-center gap-6">
                  {info.last_price && (
                    <div className="text-right">
                      <p className="text-xs text-terminal-text-muted font-mono">Price</p>
                      <p className="text-sm font-mono text-terminal-text">${info.last_price.toFixed(2)}</p>
                    </div>
                  )}
                  <div className="text-right">
                    <p className="text-xs text-terminal-text-muted font-mono">Score</p>
                    <p className="text-sm font-mono text-terminal-text">{opp.total_score?.toFixed(1)}</p>
                  </div>
                  <ScoreBadge score={opp.total_score} />
                </div>
              </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Position Summary */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-sans font-semibold text-terminal-text">Position Summary</h2>
          <span className="text-xs font-mono text-terminal-text-muted">{holdings.length} positions</span>
        </div>
        {holdings.length === 0 ? (
          <p className="text-sm text-terminal-text-muted font-mono">No positions found</p>
        ) : (
          <DataTable columns={posCols} data={holdings} />
        )}
      </div>

      {/* Daily Report */}
      {report && (
        <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <FileText size={20} className="text-terminal-green" />
            <h2 className="text-base font-sans font-semibold text-terminal-text">Daily Report — {report.report_date}</h2>
          </div>
          <p className="text-sm text-terminal-text font-sans leading-relaxed mb-4">{report.summary}</p>
          {report.sections?.length > 0 && (
            <div className="space-y-3">
              {report.sections.map((s) => (
                <div key={s.title} className="p-3 rounded-lg bg-terminal-bg-light">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-terminal-green text-xs font-mono">#</span>
                    <h3 className="text-sm font-sans font-semibold text-terminal-text">{s.title}</h3>
                  </div>
                  <p className="text-sm text-terminal-text-muted font-sans leading-relaxed ml-4">{s.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
