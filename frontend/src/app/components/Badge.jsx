import React from 'react';

export function Badge({ children, tone = 'blue' }) {
  const tones = {
    blue: 'bg-cyan-400/10 text-cyan-300 border-cyan-400/20',
    green: 'bg-emerald-400/10 text-emerald-300 border-emerald-400/20',
    yellow: 'bg-amber-400/10 text-amber-300 border-amber-400/20',
    red: 'bg-red-400/10 text-red-300 border-red-400/20',
    gray: 'bg-slate-400/10 text-slate-300 border-slate-400/20',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold ${tones[tone] || tones.blue}`}
    >
      {children}
    </span>
  );
}

export function severityTone(severity) {
  if (severity === 'CRITICAL' || severity === 'HIGH') return 'red';
  if (severity === 'MEDIUM') return 'yellow';
  return 'green';
}
