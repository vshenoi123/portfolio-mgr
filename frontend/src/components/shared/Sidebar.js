'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, Lightbulb, PieChart, Activity, Settings, HelpCircle,
} from 'lucide-react';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/opportunities', label: 'Opportunities', icon: Lightbulb },
  { href: '/portfolio', label: 'Portfolio', icon: PieChart },
  { href: '/monitoring', label: 'Monitoring', icon: Activity },
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/help', label: 'Help', icon: HelpCircle },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 h-screen bg-terminal-bg-light border-r border-terminal-border flex flex-col shrink-0">
      <div className="p-5 border-b border-terminal-border">
        <h1 className="text-terminal-green font-mono text-lg font-bold tracking-tight">
          {'>'} portfolio-mgr
        </h1>
        <p className="text-terminal-text-muted text-xs font-mono mt-1">
          v2.4.1 — active
        </p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-sans transition-colors ${
                isActive
                  ? 'bg-terminal-green/10 text-terminal-green border border-terminal-green/20'
                  : 'text-terminal-text-muted hover:text-terminal-text hover:bg-terminal-bg-hover border border-transparent'
              }`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-terminal-border">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-terminal-green opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-terminal-green" />
          </span>
          <span className="text-xs font-mono text-terminal-text-muted">System Online</span>
        </div>
      </div>
    </aside>
  );
}
