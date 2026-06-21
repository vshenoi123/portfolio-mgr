export default function RegimeDot({ regime }) {
  const r = (regime || '').toLowerCase();
  const color =
    r === 'bull' ? 'bg-terminal-green'
    : r === 'bear' ? 'bg-terminal-red'
    : 'bg-terminal-yellow';

  const label =
    r === 'bull' ? 'Bull Market'
    : r === 'bear' ? 'Bear Market'
    : 'Range Bound';

  return (
    <div className="flex items-center gap-2 font-sans">
      <span className={`inline-block w-3 h-3 rounded-full ${color}`} />
      <span className="text-sm font-medium text-terminal-text">{label}</span>
    </div>
  );
}
