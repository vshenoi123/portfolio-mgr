'use client';

import { useState, useEffect } from 'react';
import { Save, Play, RefreshCw, RotateCcw, Activity, BarChart3, AlertTriangle, FileText, Database, Settings as SettingsIcon } from 'lucide-react';
import { clearOpportunitiesCache } from '@/lib/opportunitiesCache';
import { getSettings, updateSettings } from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

const ACTIONS = [
  { id: 'sync_positions', label: 'Sync Alpaca Positions', desc: 'Pull latest positions from Alpaca paper account', icon: RotateCcw, endpoint: '/trading/sync', method: 'POST' },
  { id: 'refresh_all', label: 'Refresh Market Data', desc: 'Fetch latest OHLCV from Polygon for all tickers', icon: RefreshCw, endpoint: '/data/refresh-all', method: 'POST' },
  { id: 'refresh_spy', label: 'Refresh SPY Data', desc: 'Fetch latest SPY OHLCV from Polygon', icon: RefreshCw, endpoint: '/data/refresh/SPY?days=365', method: 'POST' },
  { id: 'generate_report', label: 'Generate Daily Report', desc: 'Generate AI-powered daily portfolio report', icon: FileText, endpoint: '/ai/report', method: 'GET' },
  { id: 'compute_opportunities', label: 'Scan Opportunities', desc: 'Compute opportunity scores for universe', icon: BarChart3, endpoint: '/opportunities/compute', method: 'POST' },
  { id: 'run_stress_test', label: 'Run Stress Test', desc: 'Run stress scenarios on current portfolio positions', icon: AlertTriangle, endpoint: '/risk/stress-test/run', method: 'GET' },
];

function ActionButton({ action, onRun, loading, result }) {
  const Icon = action.icon;
  const isLoading = loading === action.id;
  const isSuccess = result?.[action.id]?.success;
  const isError = result?.[action.id]?.error;

  return (
    <button
      onClick={() => onRun(action)}
      disabled={isLoading}
      className={`flex items-center gap-3 w-full p-3 rounded-lg border transition-colors ${
        isError ? 'border-terminal-red bg-terminal-red/10' :
        isSuccess ? 'border-terminal-green bg-terminal-green/10' :
        'border-terminal-border bg-terminal-bg hover:border-terminal-green/50 hover:bg-terminal-bg-hover'
      } ${isLoading ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
    >
      <Icon size={18} className={`${isError ? 'text-terminal-red' : isSuccess ? 'text-terminal-green' : 'text-terminal-text-muted'}`} />
      <div className="text-left flex-1">
        <div className="text-sm font-sans font-medium text-terminal-text">{action.label}</div>
        <div className="text-xs font-sans text-terminal-text-muted">{action.desc}</div>
      </div>
      {isLoading && <RefreshCw size={14} className="text-terminal-green animate-spin" />}
      {!isLoading && !isError && !isSuccess && <Play size={14} className="text-terminal-text-muted" />}
      {isSuccess && <span className="text-xs font-mono text-terminal-green">OK</span>}
      {isError && <span className="text-xs font-mono text-terminal-red">FAIL</span>}
    </button>
  );
}

const SETTING_DEFS = {
  min_options_volume: {
    label: 'Min Options Volume (30d ADV)',
    desc: 'Tickers with average daily options volume below this threshold are excluded from opportunity scans',
    type: 'number',
    icon: Database,
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState({});
  const [dirty, setDirty] = useState({});
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(null);
  const [results, setResults] = useState({});
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    getSettings()
      .then((data) => {
        setSettings(data);
        setDirty({ ...data });
      })
      .catch(() => {})
      .finally(() => setFetching(false));
  }, []);

  const handleSave = async () => {
    setSaved(false);
    const changed = {};
    for (const key of Object.keys(dirty)) {
      if (dirty[key] !== settings[key]) {
        changed[key] = dirty[key];
      }
    }
    if (Object.keys(changed).length === 0) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      return;
    }
    try {
      await updateSettings(changed);
      setSettings({ ...dirty });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // silently fail
    }
  };

  const handleRunAction = async (action) => {
    setLoading(action.id);
    setResults((prev) => ({ ...prev, [action.id]: {} }));
    try {
      const opts = { method: action.method || 'POST' };
      if (action.body) {
        opts.body = JSON.stringify(action.body);
      }
      const res = await fetch(`${API_BASE}${action.endpoint}`, opts);
      const data = await res.json();
      setResults((prev) => ({ ...prev, [action.id]: { success: true, data } }));
      if (action.id === 'refresh_all') {
        clearOpportunitiesCache();
      }
    } catch (err) {
      setResults((prev) => ({ ...prev, [action.id]: { error: err.message } }));
    } finally {
      setLoading(null);
    }
  };

  const knownKeys = Object.keys(SETTING_DEFS).filter((k) => k in dirty);

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-sans font-bold text-terminal-text">Settings</h1>
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 text-sm font-mono bg-terminal-green text-black rounded-lg hover:bg-terminal-green-dark transition-colors font-semibold"
        >
          <Save size={16} />
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      {/* System Actions */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <div className="flex items-center gap-3 mb-1">
          <Activity size={20} className="text-terminal-green" />
          <h2 className="text-base font-sans font-semibold text-terminal-text">System Actions</h2>
        </div>
        <p className="text-sm text-terminal-text-muted font-sans mb-4 ml-9">Manually trigger backend tasks</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 ml-9">
          {ACTIONS.map((action) => (
            <ActionButton
              key={action.id}
              action={action}
              onRun={handleRunAction}
              loading={loading}
              result={results}
            />
          ))}
        </div>
      </div>

      {/* Market Data Settings */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <div className="flex items-center gap-3 mb-1">
          <Database size={20} className="text-terminal-green" />
          <h2 className="text-base font-sans font-semibold text-terminal-text">Market Data</h2>
        </div>
        <p className="text-sm text-terminal-text-muted font-sans mb-4 ml-9">
          Configure data pipeline thresholds and filters
        </p>
        {fetching ? (
          <div className="ml-9 flex items-center gap-2 text-sm text-terminal-text-muted">
            <RefreshCw size={14} className="animate-spin" />
            Loading settings...
          </div>
        ) : (
          <div className="space-y-4 ml-9">
            {knownKeys.length === 0 && (
              <div className="text-sm text-terminal-text-muted">No settings loaded from backend.</div>
            )}
            {knownKeys.map((key) => {
              const def = SETTING_DEFS[key];
              const Icon = def.icon;
              return (
                <div key={key} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon size={16} className="text-terminal-text-muted" />
                    <div>
                      <label className="text-sm font-sans text-terminal-text">{def.label}</label>
                      <p className="text-xs font-sans text-terminal-text-muted">{def.desc}</p>
                    </div>
                  </div>
                  <input
                    type={def.type || 'text'}
                    className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-1.5 text-sm font-mono text-terminal-text focus:outline-none focus:border-terminal-green/50 w-36 text-right"
                    value={dirty[key] ?? ''}
                    onChange={(e) => setDirty((prev) => ({ ...prev, [key]: e.target.value }))}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Raw Settings */}
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
        <div className="flex items-center gap-3 mb-1">
          <SettingsIcon size={20} className="text-terminal-green" />
          <h2 className="text-base font-sans font-semibold text-terminal-text">All Settings</h2>
        </div>
        <p className="text-sm text-terminal-text-muted font-sans mb-4 ml-9">
          Raw key-value store from backend. Edit any setting directly.
        </p>
        {fetching ? (
          <div className="ml-9 flex items-center gap-2 text-sm text-terminal-text-muted">
            <RefreshCw size={14} className="animate-spin" />
            Loading settings...
          </div>
        ) : (
          <div className="space-y-3 ml-9">
            {Object.keys(dirty).length === 0 && (
              <div className="text-sm text-terminal-text-muted">No settings loaded.</div>
            )}
            {Object.keys(dirty).sort().map((key) => {
              const isKnown = key in SETTING_DEFS;
              return (
                <div key={key} className="flex items-center justify-between">
                  <label className="text-sm font-mono text-terminal-text">{key}</label>
                  <div className="flex items-center gap-2">
                    {!isKnown && (
                      <span className="text-[10px] font-mono text-terminal-text-muted bg-terminal-border px-1.5 py-0.5 rounded">custom</span>
                    )}
                    <input
                      type="text"
                      className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-1.5 text-sm font-mono text-terminal-text focus:outline-none focus:border-terminal-green/50 w-48 text-right"
                      value={dirty[key] ?? ''}
                      onChange={(e) => setDirty((prev) => ({ ...prev, [key]: e.target.value }))}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
