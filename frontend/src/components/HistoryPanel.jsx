import React, { useState, useEffect, useCallback } from 'react';
import { getBaseUrl } from '../utils/config';

export default function HistoryPanel({ serverIP, prefs }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const loadHistory = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/history`);
      if (!r.ok) throw new Error('History fetch failed');
      setHistory(await r.json());
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    loadHistory();
    const timer = setInterval(loadHistory, prefs.historyMs);
    return () => clearInterval(timer);
  }, [loadHistory, prefs.historyMs]);

  if (loading) {
    return <div className="text-slate-400 p-4">Carregando historico...</div>;
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm h-[calc(100vh-12rem)] min-h-[500px] flex flex-col">
      <div className="p-4 border-b border-slate-800 bg-slate-950/50 flex justify-between items-center z-10 sticky top-0 backdrop-blur-sm">
        <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">Registro Histórico de Leituras</h2>
        <a href={`${baseUrl}/api/reports/weekly/download`} className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs sm:text-sm font-bold px-4 py-2 sm:py-2.5 rounded-xl shadow-lg shadow-emerald-500/20 transition-all hover:-translate-y-0.5 whitespace-nowrap flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="hidden sm:inline-block"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
          Exportar PDF
        </a>
      </div>

      <div className="hidden sm:grid grid-cols-4 gap-4 px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800/80 bg-slate-900/90 z-10 sticky top-[73px]">
        <span>Data</span>
        <span>Hora</span>
        <span>Status</span>
        <span className="text-right">Temperatura</span>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent bg-slate-950/20">
        {history.length === 0 && <div className="p-8 text-slate-500 text-center flex flex-col items-center justify-center h-full">Nenhuma leitura registrada.</div>}

        {history.map((item) => (
          <div key={item.id} className="flex flex-col sm:grid sm:grid-cols-4 gap-2 sm:gap-4 px-4 sm:px-6 py-4 border-b border-slate-800/50 text-sm hover:bg-slate-800/20 transition-colors group">
            <div className="flex justify-between sm:block">
              <span className="text-slate-500 sm:hidden font-semibold text-xs uppercase">Data</span>
              <span className="font-medium text-slate-200">{item.data}</span>
            </div>

            <div className="flex justify-between sm:block">
              <span className="text-slate-500 sm:hidden font-semibold text-xs uppercase">Hora</span>
              <span className="font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800/80">{item.hora}</span>
            </div>

            <div className="flex justify-between sm:block">
              <span className="text-slate-500 sm:hidden font-semibold text-xs uppercase">Status</span>
              <span className={`font-bold inline-flex items-center gap-1.5 ${item.status === 'NORMAL' ? 'text-emerald-400' : 'text-rose-400'}`}>
                {item.status === 'NORMAL'
                  ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                }
                {item.status}
              </span>
            </div>

            <div className="flex justify-between sm:block sm:text-right mt-2 sm:mt-0 pt-2 sm:pt-0 border-t border-slate-800/50 sm:border-0">
              <span className="text-slate-500 sm:hidden font-semibold text-xs uppercase self-center">Temp</span>
              <span className="font-black text-lg text-white group-hover:text-amber-400 transition-colors">{item.temp} <span className="text-xs font-normal text-slate-400">°C</span></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
