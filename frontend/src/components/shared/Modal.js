'use client';

import { useEffect } from 'react';
import { X } from 'lucide-react';

export default function Modal({ isOpen, onClose, title, children }) {
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative bg-terminal-bg-card border border-terminal-border rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] overflow-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-terminal-border">
          <h2 className="text-lg font-sans font-semibold text-terminal-text">{title}</h2>
          <button onClick={onClose} className="text-terminal-text-muted hover:text-terminal-text transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}
