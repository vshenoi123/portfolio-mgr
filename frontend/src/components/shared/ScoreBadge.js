import { cn } from '@/lib/utils';

export default function ScoreBadge({ score, size = 'md' }) {
  const color =
    score >= 70 ? 'bg-terminal-green/15 text-terminal-green border-terminal-green/30'
    : score >= 40 ? 'bg-terminal-yellow/15 text-terminal-yellow border-terminal-yellow/30'
    : 'bg-terminal-red/15 text-terminal-red border-terminal-red/30';

  const sizing = size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-sm';

  return (
    <span className={cn('inline-flex items-center rounded font-mono font-medium border', color, sizing)}>
      {score}
    </span>
  );
}
