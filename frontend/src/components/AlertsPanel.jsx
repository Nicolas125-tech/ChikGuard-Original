import React, { useState, useEffect, useCallback } from 'react';
import { io } from 'socket.io-client';
import { getBaseUrl } from '../utils/config';

export default function AlertsPanel({ serverIP, prefs }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const loadAlerts = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/alerts`);
      if (!r.ok) throw new Error('Alerts fetch failed');
      setAlerts(await r.json());
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    loadAlerts();
    const timer = setInterval(loadAlerts, prefs.statusMs);

    // WebSocket listener for instant alert updates
    const socket = io(baseUrl);
    socket.on('new_alert', (data) => {
      console.log('Socket event received (AlertsPanel):', data);
      loadAlerts();
    });

    return () => {
      clearInterval(timer);
      socket.disconnect();
    };
  }, [loadAlerts, prefs.statusMs, baseUrl]);

  if (loading) {
    return <div className="text-slate-400 p-4">Carregando alertas...</div>;
  }

  return (
    <div className="space-y-3 sm:space-y-4 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-4 px-2">
        <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Alertas do Sistema</h2>
        <span className="bg-slate-800 text-slate-300 font-semibold px-3 py-1 rounded-full text-xs sm:text-sm">
          {alerts.length} ativo{alerts.length !== 1 && 's'}
        </span>
      </div>

      {alerts.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center flex flex-col items-center justify-center min-h-[200px] shadow-sm">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500 mb-4 opacity-80"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <h3 className="text-xl font-bold text-slate-200 mb-2">Tudo tranquilo</h3>
          <p className="text-slate-400">Sem alertas críticos ou advertências no momento.</p>
        </div>
      )}

      {alerts.map((alert) => (
        <div key={alert.id} className={`rounded-2xl border p-4 sm:p-5 shadow-sm transition-all hover:-translate-y-0.5 ${
          alert.nivel === 'alto'
            ? 'bg-rose-500/10 border-rose-500/30 shadow-[0_0_15px_rgba(244,63,94,0.05)]'
            : alert.nivel === 'medio'
              ? 'bg-amber-500/10 border-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.05)]'
              : 'bg-slate-900 border-slate-800'
        }`}>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 sm:gap-4 mb-2">
            <div className="flex items-center gap-3">
              {alert.nivel === 'alto' && <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-rose-500 flex-shrink-0"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>}
              {alert.nivel === 'medio' && <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500 flex-shrink-0"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>}
              {alert.nivel !== 'alto' && alert.nivel !== 'medio' && <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500 flex-shrink-0"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>}

              <div className="font-bold text-lg text-white tracking-tight">{alert.tipo}</div>
            </div>
            <div className="text-xs font-medium text-slate-400 bg-slate-950/40 px-3 py-1.5 rounded-lg whitespace-nowrap border border-slate-800/50">
              {alert.data} &middot; {alert.hora}
            </div>
          </div>
          <p className={`text-sm sm:text-base leading-relaxed pl-0 sm:pl-9 mt-1 ${alert.nivel === 'alto' ? 'text-rose-200' : alert.nivel === 'medio' ? 'text-amber-200' : 'text-slate-300'}`}>
            {alert.mensagem}
          </p>
          {alert.temperatura !== null && (
            <div className="pl-0 sm:pl-9 mt-3">
               <span className="inline-flex items-center gap-1.5 bg-slate-950/60 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/></svg>
                Temperatura Reg.: <span className="text-white">{alert.temperatura}°C</span>
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
