import React, { useState, useEffect, useCallback } from 'react';
import SystemCard from './SystemCard';
import { getBaseUrl } from '../utils/config';

export default function BirdsPanel({ token, serverIP, prefs, cameras = [], activeCamera }) {
  const [live, setLive] = useState({ count: 0, items: [] });
  const [registry, setRegistry] = useState({ count: 0, items: [] });
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);
  const farmName = cameras.find(c => c.camera_id === activeCamera)?.name || 'Granja Principal';

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
      <div className="mb-2">
        <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          Visão de Lote - <span className="text-emerald-400">{farmName}</span>
        </h2>
        <p className="text-slate-400 text-sm mt-1">Detecção e contagem de aves em tempo real.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <SystemCard label="Aves visiveis agora" value={live.count ?? 0} />
        <SystemCard label="Aves unicas vistas" value={registry.count ?? 0} />
        <SystemCard label="Snapshots salvos" value={history.length} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <LiveBirdMap items={live.items || []} />

        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-[400px] sm:h-[500px]">
          <div className="px-4 py-3 border-b border-slate-800 text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400 bg-slate-950/50 flex-shrink-0">
            Aves vivas no quadro
          </div>
          <div className="flex-1 overflow-auto">
            {live.items?.length === 0 && <div className="p-4 sm:p-6 text-slate-500 text-center">Nenhuma ave visivel no momento.</div>}
            {live.items?.map((item) => (
              <div key={item.bird_uid} className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1 sm:gap-4 px-4 py-3 border-b border-slate-800/50 hover:bg-slate-800/20 text-sm transition-colors">
                <span className="font-medium text-slate-200">ID {item.bird_uid}</span>
                <span className="text-slate-400 text-xs sm:text-sm">Conf: <span className="text-emerald-400">{Math.round((item.confidence || 0) * 100)}%</span></span>
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
                <span className="text-slate-400 text-xs sm:text-sm">Conf máx: <span className="text-emerald-400">{Math.round((item.max_confidence || 0) * 100)}%</span></span>
                <span className="text-slate-500 text-xs sm:text-sm">{item.last_seen}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function LiveBirdMap({ items }) {
  const feedWidth = 1920;
  const feedHeight = 1080;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-[300px] sm:h-[400px] lg:col-span-2 relative shadow-sm">
       <div className="px-4 py-3 border-b border-slate-800 text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400 bg-slate-950/50 flex-shrink-0 z-10 flex justify-between items-center">
          <span className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-400"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
            Mapa de Distribuição (Tempo Real)
          </span>
          <span className="bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded text-xs font-bold">{items.length} detectadas</span>
       </div>
       <div className="flex-1 relative w-full h-full bg-slate-950 overflow-hidden">
          <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'linear-gradient(#334155 1px, transparent 1px), linear-gradient(90deg, #334155 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
          
          {items.map(bird => {
             if (!bird.bbox) return null;
             const [x1, y1, x2, y2] = bird.bbox;
             const cx = (x1 + x2) / 2;
             const cy = (y1 + y2) / 2;
             const left = (cx / feedWidth) * 100;
             const top = (cy / feedHeight) * 100;

             return (
                <div key={bird.bird_uid} 
                     className="absolute flex items-center justify-center group"
                     style={{ left: `${left}%`, top: `${top}%`, transform: 'translate(-50%, -50%)' }}
                >
                  <div className="w-3 h-3 bg-emerald-500 rounded-full shadow-[0_0_12px_rgba(16,185,129,1)] animate-pulse"></div>
                  <div className="absolute bottom-full mb-1 hidden group-hover:block whitespace-nowrap bg-slate-800 text-xs text-white px-2 py-1 rounded border border-slate-700 z-20">
                    ID: {bird.bird_uid} | Conf: {Math.round(bird.confidence*100)}%
                  </div>
                </div>
             );
          })}
          {items.length === 0 && <div className="absolute inset-0 flex items-center justify-center text-slate-500 text-sm font-medium">Nenhum dado espacial recebido.</div>}
       </div>
    </div>
  );
}
