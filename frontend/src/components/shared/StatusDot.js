import { cn } from '@/lib/utils';

export default function StatusDot({ status = 'online', label }) {
  const isOnline = status === 'online';
  return (
    <div className="flex items-center gap-2">
      <span className="relative flex h-2.5 w-2.5">
        {isOnline && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-terminal-green opacity-75" />
        )}
        <span className={cn(
          'relative inline-flex rounded-full h-2.5 w-2.5',
          isOnline ? 'bg-terminal-green' : 'bg-terminal-red'
        )} />
      </span>
      {label && (
        <span className="text-xs font-mono text-terminal-text-muted">{label}</span>
      )}
    </div>
  );
}
