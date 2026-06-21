'use client';

import { useState, useEffect } from 'react';
import { Filter, RefreshCw } from 'lucide-react';
import StrategyCard from '@/components/shared/StrategyCard';
import ScoreBadge from '@/components/shared/ScoreBadge';
import PctChange from '@/components/shared/PctChange';
import { formatCurrency } from '@/lib/utils';

const STRATEGIES = ['all', 'swing', 'csp', 'leaps', 'pmcc'];

const DEMO_OPPORTUNITIES = [
  { id: 1, ticker: 'NVDA', strategy: 'PMCC', score: 92, entry: 95.50, current: 142.30, target: 145.00, premium: 3.20, roi: 18.5, days_left: 42, delta: 0.82, reason: 'Strong AI momentum, earnings beat expected' },
  { id: 2, ticker: 'AMD', strategy: 'LEAPS', score: 85, entry: 110.00, current: 158.70, target: 165.00, premium: 8.50, roi: 22.0, days_left: 180, delta: 0.75, reason: 'Data center growth accelerating' },
  { id: 3, ticker: 'TSLA', strategy: 'CSP', score: 73, entry: 220.00, current: 245.60, target: 270.00, premium: 5.80, roi: 12.4, days_left: 21, delta: 0.28, reason: 'IV elevated, good premium capture' },
  { id: 4, ticker: 'AAPL', strategy: 'SWING', score: 68, entry: 185.00, current: 199.80, target: 210.00, premium: 0, roi: 8.1, days_left: 14, delta: 0, reason: 'Technical breakout above resistance' },
  { id: 5, ticker: 'MSFT', strategy: 'LEAPS', score: 62, entry: 380.00, current: 425.10, target: 440.00, premium: 12.40, roi: 10.5, days_left: 240, delta: 0.71, reason: 'Cloud revenue growth steady' },
  { id: 6, ticker: 'GOOGL', strategy: 'SWING', score: 55, entry: 165.00, current: 172.30, target: 185.00, premium: 0, roi: 4.4, days_left: 10, delta: 0, reason: 'Ad revenue recovery play' },
  { id: 7, ticker: 'AMZN', strategy: 'CSP', score: 48, entry: 175.00, current: 181.20, target: 200.00, premium: 3.50, roi: 7.9, days_left: 35, delta: 0.22, reason: 'AWS growth stabilizing' },
  { id: 8, ticker: 'META', strategy: 'PMCC', score: 42, entry: 450.00, current: 478.50, target: 520.00, premium: 4.10, roi: 6.2, days_left: 60, delta: 0.68, reason: 'Reels monetization improving' },
];

export default function OpportunitiesPage() {
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 400);
    return () => clearTimeout(t);
  }, []);

  const filtered = filter === 'all'
    ? DEMO_OPPORTUNITIES
    : DEMO_OPPORTUNITIES.filter((o) => o.strategy.toLowerCase() === filter);

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-sans font-bold text-terminal-text">Opportunities</h1>
        <button className="flex items-center gap-2 px-3 py-2 text-sm font-mono text-terminal-green border border-terminal-green/30 rounded-lg hover:bg-terminal-green/10 transition-colors">
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={16} className="text-terminal-text-muted" />
        {STRATEGIES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 text-sm font-mono rounded-lg border transition-colors uppercase tracking-wider ${
              filter === s
                ? 'bg-terminal-green/10 text-terminal-green border-terminal-green/30'
                : 'bg-terminal-bg-card text-terminal-text-muted border-terminal-border hover:border-terminal-green/20 hover:text-terminal-text'
            }`}
          >
            {s === 'all' ? 'All' : s}
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading ? (
        <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-48 bg-terminal-bg-card rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filtered.map((opp) => (
            <StrategyCard
              key={opp.id}
              title={opp.ticker}
              score={opp.score}
              strategy={opp.strategy}
              metrics={{
                Entry: formatCurrency(opp.entry),
                Current: formatCurrency(opp.current),
                Target: formatCurrency(opp.target),
                ROI: <PctChange value={opp.roi} />,
                'Days Left': opp.days_left,
                Delta: opp.delta || '-',
              }}
            >
              <p className="text-sm text-terminal-text-muted font-sans mt-4 pt-3 border-t border-terminal-border">
                {opp.reason}
              </p>
            </StrategyCard>
          ))}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="text-center py-12">
          <p className="text-terminal-text-muted font-sans">No opportunities found for <span className="font-mono text-terminal-text">{filter}</span></p>
        </div>
      )}
    </div>
  );
}
