'use client';

import { useState } from 'react';
import { Save, Bell, Shield, DollarSign, RefreshCw, Play, RotateCcw, Activity, BarChart3, AlertTriangle, FileText } from 'lucide-react';
import StatusDot from '@/components/shared/StatusDot';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

const ACTIONS = [
  { id: 'sync_positions', label: 'Sync Alpaca Positions', desc: 'Pull latest positions from Alpaca paper account', icon: RotateCcw, endpoint: '/trading/sync', method: 'POST' },
  { id: 'refresh_all', label: 'Refresh Market Data', desc: 'Fetch latest OHLCV from Polygon for all tickers', icon: RefreshCw, endpoint: '/data/refresh-all', method: 'POST' },
  { id: 'refresh_spy', label: 'Refresh SPY Data', desc: 'Fetch latest SPY OHLCV from Polygon', icon: RefreshCw, endpoint: '/data/refresh/SPY?days=365', method: 'POST' },
  { id: 'refresh_ticker_details', label: 'Refresh Ticker Details', desc: 'Update company names, exchange, market cap for all tickers', icon: RefreshCw, endpoint: '/data/ticker-details/refresh', method: 'POST' },
  { id: 'generate_report', label: 'Generate Daily Report', desc: 'Generate AI-powered daily portfolio report', icon: FileText, endpoint: '/ai/report', method: 'GET' },
  { id: 'compute_opportunities', label: 'Scan Opportunities', desc: 'Compute opportunity scores for universe', icon: BarChart3, endpoint: '/opportunities/compute', method: 'POST' },
  { id: 'run_stress_test', label: 'Run Stress Test', desc: 'Run stress scenarios on current portfolio positions', icon: AlertTriangle, endpoint: '/risk/stress-test/run', method: 'GET' },
];

const SECTIONS = [
  {
    id: 'notifications',
    icon: Bell,
    title: 'Notifications',
    desc: 'Configure alert channels and thresholds',
    fields: [
      { key: 'email', label: 'Email Alerts', type: 'toggle', value: true },
      { key: 'sms', label: 'SMS Alerts', type: 'toggle', value: false },
      { key: 'daily_report', label: 'Daily Report', type: 'toggle', value: true },
      { key: 'threshold', label: 'Alert Threshold', type: 'select', value: '5%', options: ['1%', '2%', '5%', '10%'] },
    ],
  },
  {
    id: 'trading',
    icon: Shield,
    title: 'Trading Preferences',
    desc: 'Default strategy and risk parameters',
    fields: [
      { key: 'max_position', label: 'Max Position Size', type: 'select', value: '$25,000', options: ['$10,000', '$25,000', '$50,000', '$100,000'] },
      { key: 'max_risk', label: 'Max Risk Per Trade', type: 'select', value: '2%', options: ['1%', '2%', '3%', '5%'] },
      { key: 'auto_roll', label: 'Auto-Roll Options', type: 'toggle', value: false },
    ],
  },
  {
    id: 'api',
    icon: DollarSign,
    title: 'API Configuration',
    desc: 'Brokerage and data provider connections',
    fields: [
      { key: 'broker', label: 'Broker', type: 'text', value: 'Alpaca Paper' },
      { key: 'data_provider', label: 'Market Data', type: 'text', value: 'Polygon.io' },
      { key: 'api_status', label: 'API Status', type: 'custom', value: 'online' },
    ],
  },
  {
    id: 'display',
    icon: RefreshCw,
    title: 'Display Options',
    desc: 'Dashboard layout and refresh settings',
    fields: [
      { key: 'refresh', label: 'Auto-Refresh', type: 'select', value: '30s', options: ['15s', '30s', '60s', 'Off'] },
      { key: 'currency', label: 'Display Currency', type: 'select', value: 'USD', options: ['USD', 'EUR', 'GBP', 'CAD'] },
      { key: 'dark_mode', label: 'Dark Mode', type: 'toggle', value: true },
    ],
  },
];

function SettingField({ field }) {
  if (field.type === 'toggle') {
    return (
      <div className={`w-10 h-5 rounded-full transition-colors relative cursor-pointer ${field.value ? 'bg-terminal-green' : 'bg-terminal-border'}`}>
        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${field.value ? 'translate-x-5' : 'translate-x-0.5'}`} />
      </div>
    );
  }
  if (field.type === 'select') {
    return (
      <select className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-1.5 text-sm font-mono text-terminal-text focus:outline-none focus:border-terminal-green/50" defaultValue={field.value}>
        {field.options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  }
  if (field.type === 'custom') {
    return <StatusDot status={field.value} />;
  }
  return (
    <input
      type="text"
      className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-1.5 text-sm font-mono text-terminal-text focus:outline-none focus:border-terminal-green/50 w-48"
      defaultValue={field.value}
    />
  );
}

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

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(null);
  const [results, setResults] = useState({});

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
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
    } catch (err) {
      setResults((prev) => ({ ...prev, [action.id]: { error: err.message } }));
    } finally {
      setLoading(null);
    }
  };

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

      {SECTIONS.map((section) => {
        const Icon = section.icon;
        return (
          <div key={section.id} id={section.id} className="bg-terminal-bg-card border border-terminal-border rounded-xl p-5">
            <div className="flex items-center gap-3 mb-1">
              <Icon size={20} className="text-terminal-green" />
              <h2 className="text-base font-sans font-semibold text-terminal-text">{section.title}</h2>
            </div>
            <p className="text-sm text-terminal-text-muted font-sans mb-4 ml-9">{section.desc}</p>
            <div className="space-y-4 ml-9">
              {section.fields.map((field) => (
                <div key={field.key} className="flex items-center justify-between">
                  <label className="text-sm font-sans text-terminal-text">{field.label}</label>
                  <SettingField field={field} />
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}