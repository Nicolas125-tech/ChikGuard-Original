import React, { useState, useEffect, useCallback } from 'react';
import { Wind, Zap, Thermometer, LayoutDashboard, Download, CloudLightning, RefreshCw } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getBaseUrl } from '../utils/config';
import { isDeepEqual } from '../utils/performance';

export default function ClimatePanel({ token, serverIP, prefs, canControlDevices, cameras = [], activeCamera }) {
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [isToggling, setIsToggling] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [weather, setWeather] = useState(null);
  const [Erro_State, setErro] = useState(false);
  const baseUrl = getBaseUrl(serverIP);
  const farmName = cameras.find(c => c.camera_id === activeCamera)?.name || 'Granja Principal';

  const fetchDevices = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Device state fetch failed');
      const data = await r.json() || { ventilacao: false, aquecedor: false };
      setDispositivos(prev => isDeepEqual(prev, data) ? prev : data);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/history`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('History fetch failed');
      const data = await r.json() || [];
      setHistorico(prev => isDeepEqual(prev, data) ? prev : data);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchWeather = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/weather/forecast`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) {
        const data = await r.json();
        // Bolt Optimization: Prevent unnecessary React re-renders by skipping state updates if the polled API data is identical.
        setWeather(prev => isDeepEqual(prev, data) ? prev : data);
      }
    } catch {
      // ignore
    }
  }, [baseUrl, token]);

  useEffect(() => {
    setTimeout(() => fetchDevices(), 0);
    setTimeout(() => fetchHistory(), 0);
    setTimeout(() => fetchWeather(), 0);
    const c = setInterval(fetchDevices, prefs.devicesMs);
    const h = setInterval(fetchHistory, prefs.historyMs);
    const w = setInterval(fetchWeather, 300000); // 5 min
    return () => { clearInterval(c); clearInterval(h); clearInterval(w); };
  }, [fetchDevices, fetchHistory, fetchWeather, prefs]);

  const toggleDevice = async (tipo, ligar) => {
    if (!canControlDevices) return;
    setIsToggling(tipo);
    try {
        await fetch(`${baseUrl}/api/${tipo}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ligar }),
        });
        await fetchDevices();
    } catch (e) {
        console.error(e);
    } finally {
        setIsToggling(null);
    }
  };

  const exportHistoryToCSV = () => {
    if (!historico || historico.length === 0) return;
    const header = "Hora,Temperatura (°C)\n";
    const csvContent = historico.map(row => `${row.hora},${row.temp}`).join("\n");
    const blob = new Blob([header + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `historico_termico_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="mb-2">
        <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          Clima e Dispositivos - <span className="text-emerald-400">{farmName}</span>
        </h2>
        <p className="text-slate-400 text-sm mt-1">Monitore o clima e controle o ambiente.</p>
      </div>

      <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
        <div className="space-y-6">
          {weather?.preheat_recommended && (
          <div className="p-5 rounded-3xl border border-blue-500/30 bg-blue-900/20 shadow-sm backdrop-blur-sm animate-fade-in-down">
            <h3 className="text-blue-400 text-sm font-semibold uppercase mb-2 flex items-center gap-2 tracking-widest">
              <CloudLightning size={18} /> Alerta Meteorológico Externo
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              {weather.message}
              {weather.next_night_min_c !== undefined && <span className="block mt-1 font-mono text-xs text-blue-300">Temperatura Mín. Prevista: {weather.next_night_min_c}°C</span>}
            </p>
          </div>
        )}
        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
            <h3 className="text-slate-400 text-sm font-semibold uppercase mb-4 flex items-center gap-2 tracking-widest">
                <Thermometer size={18} className="text-rose-400" /> Controle de Dispositivos (IoT)
            </h3>
            <div className="grid grid-cols-2 gap-4 h-48">
              <button 
                aria-pressed={dispositivos.ventilacao}
                disabled={!canControlDevices || isToggling === 'ventilacao'}
                onClick={() => toggleDevice('ventilacao', !dispositivos.ventilacao)} 
                className={`border p-5 rounded-2xl flex flex-col items-center justify-center gap-3 transition-all focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none ${dispositivos.ventilacao ? 'border-blue-500/50 bg-blue-500/10 shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-slate-800 bg-slate-950 hover:border-slate-700'} ${(!canControlDevices || isToggling === 'ventilacao') ? 'opacity-50 cursor-not-allowed hidden-disabled' : 'hover:-translate-y-1'}`}
              >
                {isToggling === 'ventilacao' ? <RefreshCw aria-hidden="true" size={40} className="animate-spin text-slate-400" /> : <Wind aria-hidden="true" size={40} className={dispositivos.ventilacao ? "text-blue-400" : "text-slate-500"} />}
                <span className={`text-sm font-bold tracking-wide uppercase ${dispositivos.ventilacao ? "text-blue-300" : "text-slate-400"}`}>{isToggling === 'ventilacao' ? 'Processando...' : 'Ventilar'}</span>
              </button>
              
              <button 
                aria-pressed={dispositivos.aquecedor}
                disabled={!canControlDevices || isToggling === 'aquecedor'}
                onClick={() => toggleDevice('aquecedor', !dispositivos.aquecedor)} 
                className={`border p-5 rounded-2xl flex flex-col items-center justify-center gap-3 transition-all focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none ${dispositivos.aquecedor ? 'border-orange-500/50 bg-orange-500/10 shadow-[0_0_15px_rgba(249,115,22,0.15)]' : 'border-slate-800 bg-slate-950 hover:border-slate-700'} ${(!canControlDevices || isToggling === 'aquecedor') ? 'opacity-50 cursor-not-allowed hidden-disabled' : 'hover:-translate-y-1'}`}
              >
                {isToggling === 'aquecedor' ? <RefreshCw aria-hidden="true" size={40} className="animate-spin text-slate-400" /> : <Zap aria-hidden="true" size={40} className={dispositivos.aquecedor ? "text-orange-400" : "text-slate-500"} />}
                <span className={`text-sm font-bold tracking-wide uppercase ${dispositivos.aquecedor ? "text-orange-300" : "text-slate-400"}`}>{isToggling === 'aquecedor' ? 'Processando...' : 'Aquecer'}</span>
              </button>
            </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm h-full">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-slate-400 text-sm font-semibold uppercase flex items-center gap-2 tracking-widest">
              <LayoutDashboard size={16} className="text-amber-400" /> Histórico Térmico
            </h3>
            <button
              onClick={exportHistoryToCSV}
              disabled={historico.length === 0}
              className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              title={historico.length === 0 ? "Nenhum histórico disponível para exportar" : "Baixar em Excel/CSV"}
            >
              <Download size={14} aria-hidden="true" /> Exportar CSV
            </button>
          </div>
          <div className="h-64 w-full -ml-2">
            {historico.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historico} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="hora" stroke="#64748b" fontSize={10} tickMargin={8} />
                  <YAxis domain={['dataMin - 2', 'dataMax + 2']} stroke="#64748b" fontSize={10} tickMargin={8} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px' }} itemStyle={{ color: '#10b981', fontWeight: 'bold' }} />
                  <Line type="monotone" dataKey="temp" stroke="#10b981" strokeWidth={3} dot={{ fill: '#0f172a', stroke: '#10b981', strokeWidth: 2, r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-slate-500 text-sm font-medium bg-slate-950/30 rounded-xl">Sem dados térmicos reportados.</div>}
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}
