'use client';

import { useState, useEffect } from 'react';
import { Filter, RefreshCw, Zap, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import StrategyCard from '@/components/shared/StrategyCard';
import TradeGenerationModal from '@/components/shared/TradeGenerationModal';
import { getOpportunities } from '@/lib/api';
import { getCachedOpportunities, setCachedOpportunities, clearOpportunitiesCache } from '@/lib/opportunitiesCache';
import { isMarketOpen } from '@/lib/marketHours';

const STRATEGIES = ['all', 'swing', 'csp', 'leaps', 'pmcc'];
const ASSET_TYPES = ['stocks', 'etfs'];

const METRIC_LABELS = {
  Regime: 'R',
  Breakout: 'B',
  Trend: 'T',
  Volume: 'V',
  'Rel.Strength': 'RS',
};

function formatMarketCap(mc) {
  if (!mc) return '';
  if (mc >= 1e12) return `$${(mc / 1e12).toFixed(1)}T`;
  if (mc >= 1e9) return `$${(mc / 1e9).toFixed(1)}B`;
  if (mc >= 1e6) return `$${(mc / 1e6).toFixed(1)}M`;
  return `$${mc.toLocaleString()}`;
}

function ScoreExplanations() {
  return (
    <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
      <h2 className="text-sm font-sans font-semibold text-terminal-text mb-3">Score Guide</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs font-mono">
        <div>
          <span className="text-terminal-green font-semibold">Score</span>
          <p className="text-terminal-text-muted">Composite weighted score (0-100). Higher = stronger opportunity.</p>
        </div>
        <div>
          <span className="text-terminal-green font-semibold">Regime</span>
          <p className="text-terminal-text-muted">Market regime alignment. Bull/Range = higher, Crisis = lower.</p>
        </div>
        <div>
          <span className="text-terminal-green font-semibold">Breakout</span>
          <p className="text-terminal-text-muted">Price breakout detection. New highs with volume confirmation.</p>
        </div>
        <div>
          <span className="text-terminal-green font-semibold">Trend</span>
          <p className="text-terminal-text-muted">Trend strength via ADX-like measure. Higher = stronger trend.</p>
        </div>
        <div>
          <span className="text-terminal-green font-semibold">Volume</span>
          <p className="text-terminal-text-muted">Volume relative to average. Unusual volume = conviction signal.</p>
        </div>
        <div>
          <span className="text-terminal-green font-semibold">ML Refined</span>
          <p className="text-terminal-text-muted">XGBoost-refined score. Adjusts raw scores based on historical accuracy.</p>
        </div>
      </div>
      <p className="text-xs font-mono text-terminal-text-muted mt-3 border-t border-terminal-border pt-3">
        Click <Zap size={12} className="inline text-terminal-green" /> Generate Trade on any card to see recommended strike, DTE, and premium.
      </p>
    </div>
  );
}

function SectorSection({ sector, count, children, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="bg-terminal-bg-card border border-terminal-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-terminal-bg-light transition-colors"
      >
        <div className="flex items-center gap-3">
          {open ? <ChevronDown size={16} className="text-terminal-text-muted" /> : <ChevronRight size={16} className="text-terminal-text-muted" />}
          <h3 className="text-sm font-sans font-semibold text-terminal-text">{sector}</h3>
          <span className="px-2 py-0.5 text-xs font-mono rounded bg-terminal-bg-light text-terminal-text-muted border border-terminal-border">
            {count}
          </span>
        </div>
      </button>
      {open && (
        <div className="px-5 pb-4 overflow-x-auto">
          <div className="flex gap-4" style={{ minWidth: 'max-content' }}>
            {children}
          </div>
        </div>
      )}
    </div>
  );
}

export default function OpportunitiesPage() {
  const [filter, setFilter] = useState('all');
  const [assetFilter, setAssetFilter] = useState('stocks');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [groups, setGroups] = useState([]);
  const [tradeTicker, setTradeTicker] = useState(null);

  const cacheKey = `${filter}_${assetFilter}`;

  const fetchData = async (strategyType = 'all', assetType = 'stocks', forceRefresh = false) => {
    const cached = getCachedOpportunities(cacheKey);
    if (cached && !forceRefresh) {
      setGroups(cached.groups || []);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getOpportunities(strategyType, 50, assetType);
      setCachedOpportunities(cacheKey, data);
      setGroups(data.groups || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(filter, assetFilter); }, [filter, assetFilter]);

  const handleRefresh = () => {
    clearOpportunitiesCache();
    fetchData(filter, assetFilter, true);
  };

  const totalCards = groups.reduce((s, g) => s + g.count, 0);

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-sans font-bold text-terminal-text">Opportunities</h1>
        <button onClick={handleRefresh} className="flex items-center gap-2 px-3 py-2 text-sm font-mono text-terminal-green border border-terminal-green/30 rounded-lg hover:bg-terminal-green/10 transition-colors">
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <ScoreExplanations />

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-terminal-text-muted" />
          <span className="text-xs font-mono text-terminal-text-muted uppercase">Strategy</span>
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
        <div className="w-px h-6 bg-terminal-border" />
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-terminal-text-muted uppercase">Asset</span>
          {ASSET_TYPES.map((a) => (
            <button
              key={a}
              onClick={() => setAssetFilter(a)}
              className={`px-3 py-1.5 text-sm font-mono rounded-lg border transition-colors uppercase tracking-wider ${
                assetFilter === a
                  ? 'bg-terminal-green/10 text-terminal-green border-terminal-green/30'
                  : 'bg-terminal-bg-card text-terminal-text-muted border-terminal-border hover:border-terminal-green/20 hover:text-terminal-text'
              }`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-terminal-red/10 border border-terminal-red/30 rounded-xl p-5 flex items-center justify-between">
          <p className="text-sm font-mono text-terminal-red">{error}</p>
          <button onClick={handleRefresh} className="text-sm font-mono text-terminal-red hover:text-terminal-text transition-colors">Retry</button>
        </div>
      )}

      {loading ? (
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-terminal-bg-card rounded-xl" />
          ))}
        </div>
      ) : !error && totalCards === 0 ? (
        <div className="text-center py-12">
          <p className="text-terminal-text-muted font-sans">No {assetFilter} opportunities found for <span className="font-mono text-terminal-text">{filter}</span></p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Score legend for compact view */}
          <p className="text-xs font-mono text-terminal-text-muted">
            Score legend: <span className="text-terminal-text">R</span>=Regime <span className="text-terminal-text">B</span>=Breakout{' '}
            <span className="text-terminal-text">T</span>=Trend <span className="text-terminal-text">V</span>=Volume{' '}
            <span className="text-terminal-text">RS</span>=Rel.Strength
          </p>

          {groups.map((group, idx) => (
            <SectorSection key={group.sector} sector={group.sector} count={group.count} defaultOpen={idx < 3}>
              {group.opportunities.map((opp) => {
                const detailTags = [
                  opp.last_price ? `$${opp.last_price.toFixed(2)}` : null,
                  opp.exchange,
                  opp.asset_type === 'etf' ? 'ETF' : null,
                  formatMarketCap(opp.market_cap),
                ].filter(Boolean);

                return (
                  <StrategyCard
                    key={opp.ticker}
                    compact
                    title={opp.ticker}
                    details={detailTags}
                    score={opp.total_score}
                    strategy={opp.strategy_type}
                    metrics={{
                      Score: opp.total_score?.toFixed(1),
                      Regime: opp.regime_score?.toFixed(1),
                      Breakout: opp.breakout_score?.toFixed(1),
                      Trend: opp.trend_score?.toFixed(1),
                      Volume: opp.volume_score?.toFixed(1),
                      'Rel.Strength': opp.relative_strength_score?.toFixed(1),
                    }}
                  >
                    <button
                      onClick={() => setTradeTicker(opp.ticker)}
                      disabled={!isMarketOpen()}
                      className="w-full flex items-center justify-center gap-1.5 px-2 py-1.5 text-[11px] font-mono font-semibold text-black bg-terminal-green rounded-lg hover:bg-terminal-green-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {isMarketOpen() ? <Zap size={12} /> : <Clock size={12} />}
                      {isMarketOpen() ? 'Generate Trade' : 'Market Closed'}
                    </button>
                  </StrategyCard>
                );
              })}
            </SectorSection>
          ))}
        </div>
      )}

      {tradeTicker && (
        <TradeGenerationModal ticker={tradeTicker} onClose={() => setTradeTicker(null)} />
      )}
    </div>
  );
}
