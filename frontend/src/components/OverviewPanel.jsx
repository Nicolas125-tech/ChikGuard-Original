import React, { useState, useEffect, useCallback } from 'react';
import { Thermometer, Bird, CheckCircle, Activity } from 'lucide-react';
import { getBaseUrl } from '../utils/config';

export default function OverviewPanel({ token, serverIP, prefs }) {
  const [dados, setDados] = useState(null);
  const [contagem, setContagem] = useState(null);
  const [summary, setSummary] = useState(null);
  const baseUrl = getBaseUrl(serverIP);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/status`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) setDados(await r.json());
    } catch (e) {}
  }, [baseUrl, token]);

  const fetchCount = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/chick_count`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) {
        const d = await r.json();
        setContagem(d.count);
      }
    } catch (e) {}
  }, [baseUrl, token]);

  const fetchSummary = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/summary`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) setSummary(await r.json());
    } catch (e) {}
  }, [baseUrl, token]);

  useEffect(() => {
    fetchStatus(); fetchCount(); fetchSummary();
    const a = setInterval(fetchStatus, prefs.statusMs);
    const b = setInterval(fetchCount, prefs.countMs);
    const c = setInterval(fetchSummary, prefs.statusMs);
    return () => { clearInterval(a); clearInterval(b); clearInterval(c); };
  }, [fetchStatus, fetchCount, fetchSummary, prefs]);

  return (
    <div className="grid gap-6 grid-cols-1 md:grid-cols-3">
        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400 font-semibold text-sm uppercase tracking-widest mb-4">
            <Thermometer size={18} className="text-rose-400" /> Temperatura Média
          </div>
          <div className="text-6xl font-black text-white mb-3 tracking-tighter drop-shadow-sm">
            {dados?.temperatura ?? '--'} <span className="text-4xl text-slate-500 font-bold tracking-normal">°C</span>
          </div>
          <div className="inline-flex px-4 py-1.5 rounded-lg font-bold text-sm bg-slate-950/60 border border-white/5 shadow-inner text-slate-300">
            {dados?.status || 'Aguardando Conexão'}
          </div>
        </div>

        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 text-slate-400 font-semibold text-sm uppercase tracking-widest">
              <Bird size={18} className="text-indigo-400" /> Detecções
            </div>
            <CheckCircle className="text-emerald-500 drop-shadow-sm" size={20} />
          </div>
          <div className="text-6xl font-black text-white tracking-tighter drop-shadow-sm">
            {contagem ?? '--'} <span className="text-xl text-slate-500 font-bold tracking-normal uppercase ml-1">aves</span>
          </div>
        </div>

        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="text-sm uppercase font-semibold tracking-widest text-slate-400 mb-2 flex items-center gap-2">
            <Activity size={18} className="text-emerald-400"/> Score de Conforto
          </div>
          <div className="text-5xl font-black text-white drop-shadow-sm mt-4">
            {summary?.comfort_score ?? '--'}
          </div>
          <div className="w-full h-4 bg-slate-950 rounded-full mt-6 overflow-hidden border border-slate-800/50 shadow-inner">
            <div 
              className={`h-full transition-all duration-1000 ease-out ${Number(summary?.comfort_score || 0) >= 80 ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' : Number(summary?.comfort_score || 0) >= 60 ? 'bg-gradient-to-r from-yellow-500 to-amber-400' : 'bg-gradient-to-r from-red-600 to-rose-500'}`}
              style={{ width: `${Math.max(0, Math.min(100, Number(summary?.comfort_score || 0)))}%` }}
            />
          </div>
        </div>
    </div>
  );
}
