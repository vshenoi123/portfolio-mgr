import ScoreBadge from './ScoreBadge';
import { cn } from '@/lib/utils';

export default function StrategyCard({ title, subtitle, details, score, strategy, metrics = {}, className, children }) {
  return (
    <div className={cn('bg-terminal-bg-card border border-terminal-border rounded-xl p-5 hover:border-terminal-green/30 transition-colors', className)}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-base font-sans font-semibold text-terminal-text">{title}</h3>
          {subtitle && (
            <p className="text-xs font-sans text-terminal-text-muted mt-0.5 truncate max-w-[200px]">{subtitle}</p>
          )}
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {strategy && (
              <span className="inline-block px-2 py-0.5 text-xs font-mono rounded bg-terminal-green/10 text-terminal-green border border-terminal-green/20 uppercase tracking-wider">
                {strategy}
              </span>
            )}
            {details && details.map((d, i) => (
              <span key={i} className="inline-block px-2 py-0.5 text-xs font-mono rounded bg-terminal-bg-light text-terminal-text-muted border border-terminal-border">
                {d}
              </span>
            ))}
          </div>
        </div>
        {score != null && <ScoreBadge score={score} />}
      </div>

      {Object.keys(metrics).length > 0 && (
        <div className="grid grid-cols-2 gap-3 mt-4">
          {Object.entries(metrics).map(([key, val]) => (
            <div key={key}>
              <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">{key}</p>
              <p className="text-sm font-mono text-terminal-text mt-0.5">{val}</p>
            </div>
          ))}
        </div>
      )}

      {children}
    </div>
  );
}
