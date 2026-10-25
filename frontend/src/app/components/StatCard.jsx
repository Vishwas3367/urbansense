import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Card } from './Page';

export default function StatCard({ label, value, trend, icon: Icon }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div className="smart-icon grid h-9 w-9 place-items-center rounded-lg bg-cyan-400/10 text-cyan-300">
          <Icon size={19} />
        </div>
        <span className="smart-trend flex items-center gap-1 text-[10px] font-semibold text-emerald-300">
          <ArrowUpRight size={13} />
          {trend}
        </span>
      </div>
      <div className="smart-value mt-3 text-xl font-bold">{value}</div>
      <div className="smart-label mt-1 text-[10px] text-slate-500">{label}</div>
    </Card>
  );
}
