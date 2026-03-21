import React, { useState, useEffect, useCallback } from 'react';
import { io } from 'socket.io-client';
import { getBaseUrl } from '../utils/config';

export default function TVScreen({ serverIP, showHeader = false, onLogout }) {
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [weather, setWeather] = useState(null);
  const baseUrl = getBaseUrl(serverIP);
  const videoUrl = `${baseUrl}/api/video`;

  const load = useCallback(async () => {
    const [s, a, w] = await Promise.all([
      fetch(`${baseUrl}/api/summary`),
      fetch(`${baseUrl}/api/alerts`),
      fetch(`${baseUrl}/api/weather/forecast`),
    ]);
    if (s.ok) setSummary(await s.json());
    if (a.ok) setAlerts(await a.json());
    if (w.ok) setWeather(await w.json());
  }, [baseUrl]);

  useEffect(() => {
    const bootstrap = setTimeout(load, 0);
    const timer = setInterval(load, 4000);

    // WebSocket listener for instant updates
    const socket = io(baseUrl);
    socket.on('new_alert', (data) => {
      console.log('Socket event received (TVScreen):', data);
      load();
    });

    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
      socket.disconnect();
    };
  }, [load, baseUrl]);

  return (
    <div className="min-h-screen bg-black text-white">
      {showHeader && (
        <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-slate-800 bg-slate-950">
          <div className="font-bold text-base sm:text-lg">ChikGuard Visitante</div>
          <button onClick={onLogout} className="text-sm text-slate-300 hover:text-white bg-slate-800 px-3 py-1 rounded-md">Sair</button>
        </div>
      )}
      <div className="p-4 sm:p-6">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 bg-slate-950 border border-slate-800 rounded-2xl sm:rounded-3xl overflow-hidden flex flex-col">
            <div className="p-3 sm:p-4 border-b border-slate-800 text-lg sm:text-2xl font-bold flex-shrink-0">ChikGuard TV</div>
            <div className="flex-1 bg-black relative min-h-[300px] sm:min-h-[50vh] xl:min-h-[70vh]">
               <img src={videoUrl} alt="Camera TV" className="absolute inset-0 w-full h-full object-contain" />
            </div>
          </div>
          <div className="space-y-4 flex flex-col">
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 sm:p-6">
              <div className="text-xs uppercase text-slate-400">Temperatura</div>
              <div className="text-5xl sm:text-6xl font-black mt-1">{summary?.temperatura_atual ?? '--'}C</div>
              <div className="text-xl sm:text-2xl mt-2 font-medium">{summary?.status_atual || '--'}</div>
              <div className="text-sm text-slate-400 mt-2 bg-slate-900 inline-block px-3 py-1 rounded-full">Conforto: {summary?.comfort_score ?? '--'}/100</div>
            </div>
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 sm:p-6">
              <div className="text-xs uppercase text-slate-400 mb-2">Previsao</div>
              <div className="text-base sm:text-lg font-medium">{weather?.message || 'Sem previsao'}</div>
            </div>
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 sm:p-6 flex-1 max-h-[400px] xl:max-h-full overflow-auto">
              <div className="text-xs uppercase text-slate-400 mb-3 sticky top-0 bg-slate-950 pb-2 border-b border-slate-800">Alertas Recentes</div>
              <div className="space-y-3">
                {(alerts || []).length === 0 && <div className="text-slate-500 text-sm">Nenhum alerta.</div>}
                {(alerts || []).slice(0, 8).map((al) => (
                  <div key={al.id} className="py-2 border-b border-slate-800/50 last:border-0">
                    <div className="font-semibold text-base sm:text-lg text-white">{al.tipo}</div>
                    <div className="text-sm text-slate-400 mt-1 leading-snug">{al.mensagem}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
