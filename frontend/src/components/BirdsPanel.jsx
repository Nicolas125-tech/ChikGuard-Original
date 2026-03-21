import React, { useState, useEffect, useCallback } from 'react';
import SystemCard from './SystemCard';
import { getBaseUrl } from '../utils/config';

export default function BirdsPanel({ token, serverIP, prefs }) {
  const [live, setLive] = useState({ count: 0, items: [] });
  const [registry, setRegistry] = useState({ count: 0, items: [] });
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const loadBirds = useCallback(async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [liveRes, regRes, historyRes] = await Promise.all([
        fetch(`${baseUrl}/api/birds/live`, { headers }),
        fetch(`${baseUrl}/api/birds/registry?limit=500`, { headers }),
        fetch(`${baseUrl}/api/birds/history?limit=300`, { headers }),
      ]);
      if (liveRes.ok) setLive(await liveRes.json());
      if (regRes.ok) setRegistry(await regRes.json());
      if (historyRes.ok) setHistory(await historyRes.json());
    } finally {
      setLoading(false);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    loadBirds();
    const timer = setInterval(loadBirds, prefs.countMs);
    return () => clearInterval(timer);
  }, [loadBirds, prefs.countMs]);

  if (loading) {
    return <div className="text-slate-400 p-4">Carregando aves vistas...</div>;
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <SystemCard label="Aves visiveis agora" value={live.count ?? 0} />
        <SystemCard label="Aves unicas vistas" value={registry.count ?? 0} />
        <SystemCard label="Snapshots salvos" value={history.length} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-[400px] sm:h-[500px]">
          <div className="px-4 py-3 border-b border-slate-800 text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400 bg-slate-950/50 flex-shrink-0">
            Aves vivas no quadro
          </div>
          <div className="flex-1 overflow-auto">
            {live.items?.length === 0 && <div className="p-4 sm:p-6 text-slate-500 text-center">Nenhuma ave visivel no momento.</div>}
            {live.items?.map((item) => (
              <div key={item.bird_uid} className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1 sm:gap-4 px-4 py-3 border-b border-slate-800/50 hover:bg-slate-800/20 text-sm transition-colors">
                <span className="font-medium text-slate-200">ID {item.bird_uid}</span>
                <span className="text-slate-400 text-xs sm:text-sm">Conf: <span className="text-emerald-400">{item.confidence}</span></span>
                <span className="text-slate-500 text-xs sm:text-sm">{item.last_seen_seconds}s atrás</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-[400px] sm:h-[500px]">
          <div className="px-4 py-3 border-b border-slate-800 text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400 bg-slate-950/50 flex-shrink-0">
            Registro persistente de aves vistas
          </div>
          <div className="flex-1 overflow-auto">
            {registry.items?.length === 0 && <div className="p-4 sm:p-6 text-slate-500 text-center">Sem aves registradas ainda.</div>}
            {registry.items?.map((item) => (
              <div key={item.bird_uid} className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1 sm:gap-4 px-4 py-3 border-b border-slate-800/50 hover:bg-slate-800/20 text-sm transition-colors">
                <span className="font-medium text-slate-200">ID {item.bird_uid}</span>
                <span className="text-slate-400 text-xs sm:text-sm">Vezes: <span className="text-blue-400">{item.sightings}</span></span>
                <span className="text-slate-400 text-xs sm:text-sm">Conf máx: <span className="text-emerald-400">{item.max_confidence}</span></span>
                <span className="text-slate-500 text-xs sm:text-sm">{item.last_seen}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
