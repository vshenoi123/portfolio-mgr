'use client';

import { useState, useEffect } from 'react';
import { Filter, RefreshCw } from 'lucide-react';
import StrategyCard from '@/components/shared/StrategyCard';
import { useTickerDetails } from '@/hooks/useTickerDetails';
import { getOpportunities } from '@/lib/api';

const STRATEGIES = ['all', 'swing', 'csp', 'leaps', 'pmcc'];

function formatMarketCap(mc) {
  if (!mc) return '';
  if (mc >= 1e12) return `$${(mc / 1e12).toFixed(1)}T`;
  if (mc >= 1e9) return `$${(mc / 1e9).toFixed(1)}B`;
  if (mc >= 1e6) return `$${(mc / 1e6).toFixed(1)}M`;
  return `$${mc.toLocaleString()}`;
}

export default function OpportunitiesPage() {
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [opps, setOpps] = useState([]);

  const tickers = opps.map((o) => o.ticker);
  const { details } = useTickerDetails(tickers);

  const fetchData = async (strategyType = 'all') => {
    setLoading(true);
    setError(null);
    try {
      const data = await getOpportunities(strategyType, 20);
      setOpps(data.opportunities || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(filter); }, [filter]);

  const handleRefresh = () => fetchData(filter);

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-sans font-bold text-terminal-text">Opportunities</h1>
        <button onClick={handleRefresh} className="flex items-center gap-2 px-3 py-2 text-sm font-mono text-terminal-green border border-terminal-green/30 rounded-lg hover:bg-terminal-green/10 transition-colors">
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

      {error && (
        <div className="bg-terminal-red/10 border border-terminal-red/30 rounded-xl p-5 flex items-center justify-between">
          <p className="text-sm font-mono text-terminal-red">{error}</p>
          <button onClick={handleRefresh} className="text-sm font-mono text-terminal-red hover:text-terminal-text transition-colors">Retry</button>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-48 bg-terminal-bg-card rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {opps.map((opp, i) => {
            const info = details[opp.ticker] || {};
            const detailTags = [
              info.exchange,
              info.type === 'etf' ? 'ETF' : null,
              formatMarketCap(info.market_cap),
            ].filter(Boolean);

            return (
              <StrategyCard
                key={opp.ticker + i}
                title={opp.ticker}
                subtitle={info.name || ''}
                details={detailTags}
                score={opp.total_score}
                strategy={opp.strategy_type}
                metrics={{
                  Score: opp.total_score?.toFixed(1),
                  Regime: opp.regime_score?.toFixed(1),
                  Breakout: opp.breakout_score?.toFixed(1),
                  Trend: opp.trend_score?.toFixed(1),
                  Volume: opp.volume_score?.toFixed(1),
                }}
              >
                {opp.refined_score != null && (
                  <p className="text-xs font-mono text-terminal-text-muted mt-2 pt-2 border-t border-terminal-border">
                    ML Refined: <span className="text-terminal-green">{opp.refined_score.toFixed(1)}</span>
                  </p>
                )}
              </StrategyCard>
            );
          })}
        </div>
      )}

      {!loading && !error && opps.length === 0 && (
        <div className="text-center py-12">
          <p className="text-terminal-text-muted font-sans">No opportunities found for <span className="font-mono text-terminal-text">{filter}</span></p>
        </div>
      )}
    </div>
  );
}
