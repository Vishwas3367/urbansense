import React from 'react';

export default function Page({ title, subtitle, children, action }) {
  return (
    <div>
      <div className="mb-4 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-xl font-bold tracking-tight md:text-2xl">{title}</h1>
          {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

export function Card({ children, className = '' }) {
  return (
    <div className={`smart-card rounded-xl border border-white/10 bg-white/[.025] ${className}`}>
      {children}
    </div>
  );
}
