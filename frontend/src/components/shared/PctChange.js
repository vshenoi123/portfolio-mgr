import { cn } from '@/lib/utils';

export default function PctChange({ value }) {
  const isPos = value >= 0;
  return (
    <span className={cn('font-mono text-sm', isPos ? 'text-terminal-green' : 'text-terminal-red')}>
      {isPos ? '+' : ''}{value.toFixed(2)}%
    </span>
  );
}
