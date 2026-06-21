'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, FileText, AlertTriangle } from 'lucide-react';
import RegimeDot from '@/components/shared/RegimeDot';
import PctChange from '@/components/shared/PctChange';
import ScoreBadge from '@/components/shared/ScoreBadge';
import DataTable from '@/components/shared/DataTable';
import StrategyCard from '@/components/shared/StrategyCard';
import { formatCurrency, formatNumber } from '@/lib/utils';

const DEMO_REGIME = { regime: 'bull', description: 'Bull Market — Strong upward momentum across all sectors' };

const DEMO_HEALTH = { score: 78, total_value: 245000, cash: 85000, invested: 160000, daily_change: 1.42 };

const DEMO_OPPS = [
  { id: 1, ticker: 'NVDA', strategy: 'PMCC', score: 92, entry: 95.50, target: 145.00, premium: 3.20, roi: 18.5 },
  { id: 2, ticker: 'AMD', strategy: 'LEAPS', score: 85, entry: 110.00, target: 165.00, premium: 8.50, roi: 22.0 },
  { id: 3, ticker: 'TSLA', strategy: 'CSP', score: 73, entry: 220.00, target: 270.00, premium: 5.80, roi: 12.4 },
  { id: 4, ticker: 'AAPL', strategy: 'Swing', score: 68, entry: 185.00, target: 210.00, premium: 0, roi: 8.1 },
  { id: 5, ticker: 'MSFT', strategy: 'LEAPS', score: 62, entry: 380.00, target: 440.00, premium: 12.40, roi: 10.5 },
];

const DEMO_POSITIONS = [
  { id: 1, ticker: 'NVDA', shares: 100, avg_price: 95.50, current: 142.30, pnl: 4680.00, pnl_pct: 49.0 },
  { id: 2, ticker: 'AMD', shares: 200, avg_price: 110.00, current: 158.70, pnl: 9740.00, pnl_pct: 44.3 },
  { id: 3, ticker: 'TSLA', shares: 50, avg_price: 220.00, current: 245.60, pnl: 1280.00, pnl_pct: 11.6 },
  { id: 4, ticker: 'AAPL', shares: 150, avg_price: 185.00, current: 199.80, pnl: 2220.00, pnl_pct: 8.0 },
];

const DEMO_REPORT = {
  title: 'Market Summary — June 21, 2026',
  summary: 'Markets remain bullish with tech leading gains. NVDA continues its strong run on AI demand. Portfolio performance exceeds benchmarks by 320bps YTD. Consider taking profits on TSLA CSP position as IV contracts.',
  sections: [
    { heading: 'Macro', content: 'Fed held rates steady. CPI data coming next week. Market pricing in 60% chance of cut in September.' },
    { heading: 'Portfolio', content: 'Current allocation: 65% equities, 20% cash, 10% options, 5% bonds. Cash position provides dry powder for upcoming opportunities.' },
    { heading: 'Risk', content: 'Concentration risk in semiconductors (40% of portfolio). Consider diversifying into healthcare and energy sectors.' },
  ],
};

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

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) return <LoadingSkeleton />;

  const posCols = [
    { key: 'ticker', label: 'Ticker' },
    { key: 'shares', label: 'Shares', render: (v) => formatNumber(v) },
    { key: 'avg_price', label: 'Avg Price', render: (v) => formatCurrency(v) },
    { key: 'current', label: 'Current', render: (v) => formatCurrency(v) },
    { key: 'pnl', label: 'P&L', render: (v) => <span className={v >= 0 ? 'text-terminal-green' : 'text-terminal-red'}>{formatCurrency(v)}</span> },
    { key: 'pnl_pct', label: 'P&L %', render: (v) => <PctChange value={v} /> },
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
          {DEMO_REGIME.regime === 'bull' ? (
            <TrendingUp size={28} className="text-terminal-green" />
          ) : DEMO_REGIME.regime === 'bear' ? (
            <TrendingDown size={28} className="text-terminal-red" />
          ) : (
            <Activity size={28} className="text-terminal-yellow" />
          )}
          <div>
            <RegimeDot regime={DEMO_REGIME.regime} />
            <p className="text-sm text-terminal-text-muted font-sans mt-1">{DEMO_REGIME.description}</p>
          </div>
        </div>
      </div>

      {/* Health + Top Opportunities */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <StrategyCard title="Portfolio Health" score={DEMO_HEALTH.score} className="flex flex-col items-center">
          <div className="mt-2">
            <HealthGauge score={DEMO_HEALTH.score} />
          </div>
          <div className="w-full mt-4 space-y-2 border-t border-terminal-border pt-4">
            <div className="flex justify-between text-sm font-mono">
              <span className="text-terminal-text-muted">Total Value</span>
              <span className="text-terminal-text">{formatCurrency(DEMO_HEALTH.total_value)}</span>
            </div>
            <div className="flex justify-between text-sm font-mono">
              <span className="text-terminal-text-muted">Cash</span>
              <span className="text-terminal-green">{formatCurrency(DEMO_HEALTH.cash)}</span>
            </div>
            <div className="flex justify-between text-sm font-mono">
              <span className="text-terminal-text-muted">Invested</span>
              <span className="text-terminal-text">{formatCurrency(DEMO_HEALTH.invested)}</span>
            </div>
            <div className="flex justify-between text-sm font-mono">
              <span className="text-terminal-text-muted">Daily Change</span>
              <PctChange value={DEMO_HEALTH.daily_change} />
            </div>
          </div>
        </StrategyCard>

        <div className="lg:col-span-2 bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-sans font-semibold text-terminal-text">Top Opportunities</h2>
            <span className="text-xs font-mono text-terminal-text-muted">Score weighted</span>
          </div>
          <div className="space-y-3">
            {DEMO_OPPS.slice(0, 5).map((opp) => (
              <div key={opp.id} className="flex items-center justify-between p-3 rounded-lg bg-terminal-bg-light hover:bg-terminal-bg-hover transition-colors">
                <div className="flex items-center gap-4">
                  <span className="font-mono font-semibold text-terminal-text w-16">{opp.ticker}</span>
                  <span className="px-2 py-0.5 text-xs font-mono rounded bg-terminal-green/10 text-terminal-green border border-terminal-green/20 uppercase tracking-wider">{opp.strategy}</span>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-xs text-terminal-text-muted font-mono">Target</p>
                    <p className="text-sm font-mono text-terminal-text">{formatCurrency(opp.target)}</p>
                  </div>
                  <ScoreBadge score={opp.score} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Position Summary */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-sans font-semibold text-terminal-text">Position Summary</h2>
          <span className="text-xs font-mono text-terminal-text-muted">{DEMO_POSITIONS.length} positions</span>
        </div>
        <DataTable columns={posCols} data={DEMO_POSITIONS} />
      </div>

      {/* Daily Report */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <FileText size={20} className="text-terminal-green" />
          <h2 className="text-base font-sans font-semibold text-terminal-text">{DEMO_REPORT.title}</h2>
        </div>
        <p className="text-sm text-terminal-text font-sans leading-relaxed mb-4">{DEMO_REPORT.summary}</p>
        <div className="space-y-3">
          {DEMO_REPORT.sections.map((s) => (
            <div key={s.heading} className="p-3 rounded-lg bg-terminal-bg-light">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-terminal-green text-xs font-mono">#</span>
                <h3 className="text-sm font-sans font-semibold text-terminal-text">{s.heading}</h3>
              </div>
              <p className="text-sm text-terminal-text-muted font-sans leading-relaxed ml-4">{s.content}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
