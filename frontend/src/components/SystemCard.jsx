import React from 'react';
import { Database } from 'lucide-react';

export default function SystemCard({ label, value }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-wider text-slate-400">{label}</span>
        <Database size={16} className="text-slate-500" />
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
