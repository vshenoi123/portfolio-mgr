'use client';

import { useState } from 'react';
import { Save, Bell, Shield, DollarSign, RefreshCw } from 'lucide-react';
import StatusDot from '@/components/shared/StatusDot';

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
      { key: 'broker', label: 'Broker', type: 'text', value: 'Interactive Brokers' },
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

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
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
