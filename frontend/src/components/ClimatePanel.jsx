import React, { useState, useEffect, useCallback } from 'react';
import { Wind, Zap, Thermometer, LayoutDashboard } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getBaseUrl } from '../utils/config';

export default function ClimatePanel({ token, serverIP, prefs, canControlDevices }) {
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [historico, setHistorico] = useState([]);
  const [erro, setErro] = useState(false);
  const baseUrl = getBaseUrl(serverIP);

  const fetchDevices = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Device state fetch failed');
      const data = await r.json();
      setDispositivos(data || { ventilacao: false, aquecedor: false });
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/history`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('History fetch failed');
      const data = await r.json();
      setHistorico(data || []);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    fetchDevices();
    fetchHistory();
    const c = setInterval(fetchDevices, prefs.devicesMs);
    const h = setInterval(fetchHistory, prefs.historyMs);
    return () => { clearInterval(c); clearInterval(h); };
  }, [fetchDevices, fetchHistory, prefs]);

  const toggleDevice = async (tipo, ligar) => {
    if (!canControlDevices) return;
    try {
        await fetch(`${baseUrl}/api/${tipo}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ligar }),
        });
        fetchDevices();
    } catch (e) {
        console.error(e);
    }
  };

  return (
    <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
      <div className="space-y-6">
        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
            <h3 className="text-slate-400 text-sm font-semibold uppercase mb-4 flex items-center gap-2 tracking-widest">
                <Thermometer size={18} className="text-rose-400" /> Controle de Dispositivos (IoT)
            </h3>
            <div className="grid grid-cols-2 gap-4 h-48">
              <button 
                disabled={!canControlDevices} 
                onClick={() => toggleDevice('ventilacao', !dispositivos.ventilacao)} 
                className={`border p-5 rounded-2xl flex flex-col items-center justify-center gap-3 transition-all ${dispositivos.ventilacao ? 'border-blue-500/50 bg-blue-500/10 shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-slate-800 bg-slate-950 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed hidden-disabled' : 'hover:-translate-y-1'}`}
              >
                <Wind size={40} className={dispositivos.ventilacao ? "text-blue-400" : "text-slate-500"} />
                <span className={`text-sm font-bold tracking-wide uppercase ${dispositivos.ventilacao ? "text-blue-300" : "text-slate-400"}`}>Ventilar</span>
              </button>
              
              <button 
                disabled={!canControlDevices} 
                onClick={() => toggleDevice('aquecedor', !dispositivos.aquecedor)} 
                className={`border p-5 rounded-2xl flex flex-col items-center justify-center gap-3 transition-all ${dispositivos.aquecedor ? 'border-orange-500/50 bg-orange-500/10 shadow-[0_0_15px_rgba(249,115,22,0.15)]' : 'border-slate-800 bg-slate-950 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed hidden-disabled' : 'hover:-translate-y-1'}`}
              >
                <Zap size={40} className={dispositivos.aquecedor ? "text-orange-400" : "text-slate-500"} />
                <span className={`text-sm font-bold tracking-wide uppercase ${dispositivos.aquecedor ? "text-orange-300" : "text-slate-400"}`}>Aquecer</span>
              </button>
            </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm h-full">
          <h3 className="text-slate-400 text-sm font-semibold uppercase mb-4 flex items-center gap-2 tracking-widest">
            <LayoutDashboard size={16} className="text-amber-400" /> Histórico Térmico
          </h3>
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
  );
}
