'use client';

import { ArrowRight, Database, Brain, Lightbulb, Target, Shield, Zap, Activity, FileText, RefreshCw } from 'lucide-react';

const phases = [
  {
    icon: Database,
    title: '1. Data Ingestion',
    schedule: 'Daily (Celery beat)',
    color: 'text-terminal-blue',
    description: 'Fetches OHLCV price data from Polygon API for 64+ tickers in your universe. Data is stored as Parquet files partitioned by ticker and date.',
    details: [
      'Universe includes mega-cap stocks, growth names, and ETFs',
      'Refreshes SPY data for market regime analysis',
      'Historical data powers all downstream analysis',
    ],
    action: 'Settings → Refresh Market Data',
  },
  {
    icon: Brain,
    title: '2. Analysis Engines',
    schedule: 'Daily (Celery beat)',
    color: 'text-terminal-purple',
    description: 'Four engines process raw price data to detect patterns, trends, and anomalies that signal trading opportunities.',
    details: [
      'Feature Engineering — technical indicators (RSI, MACD, BB, ATR, OBV) for each ticker',
      'Market Regime — Hidden Markov Model classifies market as bull, bear, or range-bound',
      'CUSUM — detects structural breaks in price trends',
      'Breakout Detection — identifies support/resistance levels and breakout signals',
    ],
    action: 'Runs automatically after data refresh',
  },
  {
    icon: Lightbulb,
    title: '3. Opportunity Scoring',
    schedule: 'Daily (Celery beat)',
    color: 'text-terminal-green',
    description: 'Combines signals from all analysis engines into a single composite score (0–100) for each ticker. Optionally refined by XGBoost ML model.',
    details: [
      'Weighted combination of regime, breakout, CUSUM, volume, and trend scores',
      'ML refinement uses historical signal outcomes to improve accuracy',
      'Ranked by score — top opportunities surface first',
    ],
    action: 'Opportunities page shows live scores',
  },
  {
    icon: Target,
    title: '4. Strategy Selection',
    schedule: 'Daily (Celery beat)',
    color: 'text-terminal-yellow',
    description: 'Maps each opportunity to a specific options strategy based on your target horizon (30–45 DTE CSP, 12–24mo LEAPS, PMCC, covered calls).',
    details: [
      'CSP (Cash-Secured Put) — income on stocks you want to own',
      'LEAPS — long-dated calls for multi-month directional plays',
      'PMCC (Poor Man\'s Covered Call) — leveraged income via diagonal spreads',
      'Swing trades — directional equity positions with trailing stops',
    ],
    action: 'Opportunities page shows recommended strategy per ticker',
  },
  {
    icon: Shield,
    title: '5. Portfolio & Risk',
    schedule: 'Daily + on-demand',
    color: 'text-terminal-red',
    description: 'Tracks portfolio state, enforces risk limits, and validates every trade before execution.',
    details: [
      'Position sizing via Kelly Criterion (25% fraction)',
      'Sector exposure capped at 30%, max position 15%',
      'Trade validation checks all limits before placing orders',
      'Opportunity cost ranking — compares current holdings against new candidates',
    ],
    action: 'Portfolio page shows health score, holdings, and allocation',
  },
  {
    icon: Zap,
    title: '6. Trade Execution',
    schedule: 'On-demand + auto-sync',
    color: 'text-terminal-orange',
    description: 'Connects to Alpaca paper trading API to execute validated trades and sync positions.',
    details: [
      'All trades go through risk validation first',
      'Positions sync every 5 minutes from Alpaca',
      'Position watchdog evaluates CSP/LEAPS/PMCC/Swing exits hourly',
      'Trailing stops and profit targets managed automatically',
    ],
    action: 'Settings → Sync Alpaca Positions',
  },
  {
    icon: Activity,
    title: '7. Monitoring & AI',
    schedule: 'Continuous + daily',
    color: 'text-terminal-green',
    description: 'Tracks portfolio health, generates AI reports, and learns from trade outcomes.',
    details: [
      'Health score combines drawdown, concentration, beta, and exposure metrics',
      'Daily AI report summarizes market conditions and portfolio status',
      'Signal efficacy tracking — learns which signals predict profitable trades',
      'Trade journal logs entries/exits and computes signal effectiveness',
    ],
    action: 'Monitoring page shows health and alerts',
  },
];

const scheduleData = [
  { task: 'Position sync', frequency: 'Every 5 min', source: 'Alpaca API' },
  { task: 'Monitoring data', frequency: 'Every 5 min', source: 'Portfolio DB' },
  { task: 'Position watchdog', frequency: 'Hourly', source: 'Alpaca + Analysis' },
  { task: 'Data refresh', frequency: 'Daily', source: 'Polygon API' },
  { task: 'Analysis engines', frequency: 'Daily', source: 'OHLCV data' },
  { task: 'Opportunity scoring', frequency: 'Daily', source: 'Analysis signals' },
  { task: 'Strategy selection', frequency: 'Daily', source: 'Scores + Universe' },
  { task: 'Portfolio snapshot', frequency: 'Daily', source: 'Alpaca positions' },
  { task: 'Risk assessment', frequency: 'Daily', source: 'Portfolio state' },
  { task: 'AI daily report', frequency: 'Daily', source: 'Portfolio + Market' },
  { task: 'Monte Carlo simulation', frequency: 'Daily', source: 'Historical data' },
  { task: 'Signal efficacy', frequency: 'Daily', source: 'Trade journal' },
  { task: 'Stress testing', frequency: 'Weekly', source: 'Portfolio + Scenarios' },
];

export default function HelpPage() {
  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-sans font-bold text-terminal-text">Help</h1>
        <p className="text-sm text-terminal-text-muted font-sans mt-1">
          How the portfolio management pipeline works and how to use it effectively.
        </p>
      </div>

      {/* Overview */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-6">
        <h2 className="text-lg font-sans font-semibold text-terminal-text mb-3">System Overview</h2>
        <p className="text-sm text-terminal-text font-sans leading-relaxed">
          This system runs an automated trading pipeline on a daily cycle. Market data flows in from Polygon API,
          gets analyzed by multiple engines, scores are computed, strategies are selected, and trades are executed
          via Alpaca paper trading. The entire pipeline runs on Celery beat schedules with Redis as the message broker.
        </p>
        <div className="mt-4 p-4 rounded-lg bg-terminal-bg-light border border-terminal-border">
          <p className="text-xs font-mono text-terminal-text-muted">
            <span className="text-terminal-green">Architecture:</span> Modular monolith — FastAPI backend, Next.js frontend,
            DuckDB + Parquet for data, Redis for task queue. Deployed on Oracle Cloud Free Tier.
          </p>
        </div>
      </div>

      {/* Pipeline Phases */}
      <div>
        <h2 className="text-lg font-sans font-semibold text-terminal-text mb-4">The Pipeline — 7 Phases</h2>
        <div className="space-y-4">
          {phases.map((phase, i) => {
            const Icon = phase.icon;
            return (
              <div key={i} className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
                <div className="flex items-start gap-4">
                  <div className={`mt-0.5 ${phase.color}`}>
                    <Icon size={22} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-base font-sans font-semibold text-terminal-text">{phase.title}</h3>
                      <span className="px-2 py-0.5 text-xs font-mono rounded bg-terminal-bg-light text-terminal-text-muted border border-terminal-border">
                        {phase.schedule}
                      </span>
                    </div>
                    <p className="text-sm text-terminal-text font-sans leading-relaxed mb-3">{phase.description}</p>
                    <ul className="space-y-1.5 mb-3">
                      {phase.details.map((d, j) => (
                        <li key={j} className="flex items-start gap-2 text-sm text-terminal-text-muted font-sans">
                          <span className="text-terminal-green mt-1.5 text-xs">&#9656;</span>
                          {d}
                        </li>
                      ))}
                    </ul>
                    <div className="flex items-center gap-2 text-xs font-mono text-terminal-green">
                      <ArrowRight size={12} />
                      {phase.action}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Data Flow */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-6">
        <h2 className="text-lg font-sans font-semibold text-terminal-text mb-3">Data Flow</h2>
        <div className="font-mono text-sm text-terminal-text-muted space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-terminal-blue">Polygon API</span>
            <ArrowRight size={14} className="text-terminal-text-muted" />
            <span>Parquet files</span>
            <ArrowRight size={14} className="text-terminal-text-muted" />
            <span>DuckDB</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-terminal-purple">Analysis Engines</span>
            <ArrowRight size={14} className="text-terminal-text-muted" />
            <span>Signal Parquets</span>
            <ArrowRight size={14} className="text-terminal-text-muted" />
            <span>Opportunity Scores</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-terminal-green">Strategy + Risk</span>
            <ArrowRight size={14} className="text-terminal-text-muted" />
            <span>Validated Trades</span>
            <ArrowRight size={14} className="text-terminal-text-muted" />
            <span className="text-terminal-orange">Alpaca API</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-terminal-red">Monitoring</span>
            <ArrowRight size={14} className="text-terminal-text-muted" />
            <span>Health Score + Alerts</span>
            <ArrowRight size={14} className="text-terminal-text-muted" />
            <span>Dashboard UI</span>
          </div>
        </div>
      </div>

      {/* Schedule Table */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-6">
        <h2 className="text-lg font-sans font-semibold text-terminal-text mb-4">Automated Task Schedule</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="border-b border-terminal-border">
                <th className="text-left py-2 text-terminal-text-muted font-medium">Task</th>
                <th className="text-left py-2 text-terminal-text-muted font-medium">Frequency</th>
                <th className="text-left py-2 text-terminal-text-muted font-medium">Data Source</th>
              </tr>
            </thead>
            <tbody>
              {scheduleData.map((row, i) => (
                <tr key={i} className="border-b border-terminal-border/50">
                  <td className="py-2 text-terminal-text">{row.task}</td>
                  <td className="py-2 text-terminal-text-muted">{row.frequency}</td>
                  <td className="py-2 text-terminal-text-muted">{row.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* How to Use */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-6">
        <h2 className="text-lg font-sans font-semibold text-terminal-text mb-4">How to Use Effectively</h2>
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-sans font-semibold text-terminal-text mb-1">First Time Setup</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm text-terminal-text-muted font-sans">
              <li>Go to <span className="font-mono text-terminal-green">Settings</span> and click <span className="font-mono text-terminal-green">Refresh Market Data</span> to populate historical prices</li>
              <li>Click <span className="font-mono text-terminal-green">Scan Opportunities</span> to compute scores across your universe</li>
              <li>Click <span className="font-mono text-terminal-green">Sync Alpaca Positions</span> to import your current paper account holdings</li>
              <li>Review the <span className="font-mono text-terminal-green">Dashboard</span> for portfolio health and top opportunities</li>
            </ol>
          </div>
          <div>
            <h3 className="text-sm font-sans font-semibold text-terminal-text mb-1">Daily Workflow</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm text-terminal-text-muted font-sans">
              <li>Check <span className="font-mono text-terminal-green">Dashboard</span> each morning — market regime, health score, and top opportunities update automatically</li>
              <li>Review <span className="font-mono text-terminal-green">Opportunities</span> page — filter by strategy type (CSP, LEAPS, PMCC, Swing)</li>
              <li>Check <span className="font-mono text-terminal-green">Portfolio</span> page — verify positions and P&amp;L</li>
              <li>Check <span className="font-mono text-terminal-green">Monitoring</span> page — review alerts and system health</li>
              <li>Use <span className="font-mono text-terminal-green">Settings</span> to trigger manual actions when needed</li>
            </ol>
          </div>
          <div>
            <h3 className="text-sm font-sans font-semibold text-terminal-text mb-1">Key Concepts</h3>
            <ul className="space-y-1.5 text-sm text-terminal-text-muted font-sans">
              <li><span className="font-mono text-terminal-green">Opportunity Score (0–100)</span> — higher = stronger signal. Combines regime, breakout, trend, volume, and CUSUM analysis.</li>
              <li><span className="font-mono text-terminal-green">Health Score (0–100)</span> — higher = healthier portfolio. Penalized by drawdown, concentration, high beta, and low cash.</li>
              <li><span className="font-mono text-terminal-green">Regime</span> — bull/bear/range classification from HMM model on SPY. Influences strategy selection and position sizing.</li>
              <li><span className="font-mono text-terminal-green">Kelly Criterion</span> — position sizing formula that balances edge and variance. Uses 25% fraction for safety.</li>
              <li><span className="font-mono text-terminal-green">Signal Efficacy</span> — tracks which analysis signals actually predicted profitable trades over time.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts placeholder */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-6">
        <h2 className="text-lg font-sans font-semibold text-terminal-text mb-3">Troubleshooting</h2>
        <div className="space-y-3 text-sm font-sans">
          <div>
            <p className="text-terminal-text font-medium">Opportunities page is empty</p>
            <p className="text-terminal-text-muted">Run <span className="font-mono text-terminal-green">Scan Opportunities</span> from Settings. The pipeline needs fresh signals to score.</p>
          </div>
          <div>
            <p className="text-terminal-text font-medium">Portfolio shows no positions</p>
            <p className="text-terminal-text-muted">Click <span className="font-mono text-terminal-green">Sync Alpaca Positions</span> in Settings. Positions sync automatically every 5 minutes.</p>
          </div>
          <div>
            <p className="text-terminal-text font-medium">Health score is low</p>
            <p className="text-terminal-text-muted">Check Monitoring page for alerts. Common causes: high concentration in one sector, low cash reserve, or high portfolio beta.</p>
          </div>
          <div>
            <p className="text-terminal-text font-medium">Data seems stale</p>
            <p className="text-terminal-text-muted">Run <span className="font-mono text-terminal-green">Refresh Market Data</span> from Settings. Data refreshes daily via Celery beat, but manual refresh is instant.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
