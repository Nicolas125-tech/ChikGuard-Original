import React, { useState, useEffect, useCallback } from 'react';
import { Cpu, Wind, Zap, SlidersHorizontal } from 'lucide-react';
import { getBaseUrl } from '../utils/config';

export default function DevicesPanel({ token, serverIP, canControlDevices }) {
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [autoMode, setAutoMode] = useState({ enabled: false, effective_targets: null });
  const [lightPct, setLightPct] = useState(0);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const loadDevices = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Device state fetch failed');
      setDispositivos(await r.json());
      const auto = await fetch(`${baseUrl}/api/auto-mode`, { headers: { Authorization: `Bearer ${token}` } });
      if (auto.ok) setAutoMode(await auto.json());
      const l = await fetch(`${baseUrl}/api/luz-dimmer`, { headers: { Authorization: `Bearer ${token}` } });
      if (l.ok) {
        const j = await l.json();
        setLightPct(Number(j.luz_intensidade_pct || 0));
      }
    } finally {
      setLoading(false);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  const toggleDevice = async (tipo, ligar) => {
    if (!canControlDevices) return;
    await fetch(`${baseUrl}/api/${tipo}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ligar }),
    });
    loadDevices();
  };

  const toggleAuto = async (enabled) => {
    if (!canControlDevices) return;
    await fetch(`${baseUrl}/api/auto-mode`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
    loadDevices();
  };

  const setDimmer = async (value) => {
    if (!canControlDevices) return;
    setLightPct(value);
    await fetch(`${baseUrl}/api/luz-dimmer`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ intensidade_pct: Number(value) }),
    });
  };

  if (loading) {
    return <div className="text-slate-400 p-4">Carregando dispositivos...</div>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
      <button disabled={!canControlDevices} onClick={() => toggleAuto(!autoMode.enabled)} className={`rounded-3xl border p-6 sm:p-8 text-left transition-all ${autoMode.enabled ? 'bg-emerald-600/10 border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.1)]' : 'bg-slate-900 border-slate-800 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-1'}`}>
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-2xl ${autoMode.enabled ? 'bg-emerald-500/20' : 'bg-slate-800/50'}`}>
            <Cpu className={autoMode.enabled ? 'text-emerald-400' : 'text-slate-400'} size={28} />
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase ${autoMode.enabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
            {autoMode.enabled ? 'Auto ON' : 'Manual'}
          </span>
        </div>
        <h3 className="font-bold text-xl sm:text-2xl text-white mb-2 tracking-tight">Termostato IA</h3>
        <p className="text-slate-400 text-sm leading-relaxed mb-4">Gerenciamento dinâmico de clima com histerese inteligente.</p>
        {autoMode.effective_targets && (
          <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/50">
            <p className="text-sm font-medium text-slate-300">Target Ativo:</p>
            <div className="flex justify-between items-center mt-2">
              <span className="text-blue-400 text-xs sm:text-sm font-semibold flex items-center gap-1"><Wind size={14}/> {autoMode.effective_targets.fan_on_temp}°C</span>
              <span className="text-orange-400 text-xs sm:text-sm font-semibold flex items-center gap-1"><Zap size={14}/> {autoMode.effective_targets.heater_on_temp}°C</span>
            </div>
          </div>
        )}
      </button>

      <button disabled={!canControlDevices} onClick={() => toggleDevice('ventilacao', !dispositivos.ventilacao)} className={`rounded-3xl border p-6 sm:p-8 text-left transition-all ${dispositivos.ventilacao ? 'bg-blue-600/10 border-blue-500/40 shadow-[0_0_20px_rgba(59,130,246,0.1)]' : 'bg-slate-900 border-slate-800 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-1'}`}>
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-2xl ${dispositivos.ventilacao ? 'bg-blue-500/20' : 'bg-slate-800/50'}`}>
            <Wind className={dispositivos.ventilacao ? 'text-blue-400' : 'text-slate-400'} size={28} />
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase ${dispositivos.ventilacao ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-800 text-slate-400'}`}>
            {dispositivos.ventilacao ? 'Ligado' : 'Desligado'}
          </span>
        </div>
        <h3 className="font-bold text-xl sm:text-2xl text-white mb-2 tracking-tight">Exaustores</h3>
        <p className="text-slate-400 text-sm leading-relaxed">Renovação de ar, controle de umidade e resfriamento do galpão.</p>
      </button>

      <button disabled={!canControlDevices} onClick={() => toggleDevice('aquecedor', !dispositivos.aquecedor)} className={`rounded-3xl border p-6 sm:p-8 text-left transition-all ${dispositivos.aquecedor ? 'bg-orange-600/10 border-orange-500/40 shadow-[0_0_20px_rgba(249,115,22,0.1)]' : 'bg-slate-900 border-slate-800 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-1'}`}>
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-2xl ${dispositivos.aquecedor ? 'bg-orange-500/20' : 'bg-slate-800/50'}`}>
            <Zap className={dispositivos.aquecedor ? 'text-orange-400' : 'text-slate-400'} size={28} />
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase ${dispositivos.aquecedor ? 'bg-orange-500/20 text-orange-400' : 'bg-slate-800 text-slate-400'}`}>
            {dispositivos.aquecedor ? 'Ligado' : 'Desligado'}
          </span>
        </div>
        <h3 className="font-bold text-xl sm:text-2xl text-white mb-2 tracking-tight">Campânulas</h3>
        <p className="text-slate-400 text-sm leading-relaxed">Aquecimento radiante para conforto térmico em fases iniciais.</p>
      </button>

      <div className="rounded-3xl border p-6 sm:p-8 text-left bg-slate-900 border-slate-800 md:col-span-2 lg:col-span-3">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-slate-800/50">
              <SlidersHorizontal className="text-amber-400" size={24} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">Iluminação Gradual</h3>
              <p className="text-slate-400 text-sm">Controle de intensidade e fotoperíodo (0-100%).</p>
            </div>
          </div>
          <div className="bg-slate-950 px-4 py-2 rounded-xl border border-slate-800 text-xl font-black text-amber-400 shadow-inner">
            {lightPct}%
          </div>
        </div>

        <div className="relative pt-4 pb-2">
          <input disabled={!canControlDevices} type="range" min="0" max="100" value={lightPct} onChange={(e) => setLightPct(Number(e.target.value))} onMouseUp={(e) => setDimmer(Number(e.currentTarget.value))} onTouchEnd={(e) => setDimmer(Number(e.currentTarget.value))}
            className={`w-full h-3 bg-slate-800 rounded-full appearance-none outline-none focus:ring-2 focus:ring-amber-500/50 transition-all ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:h-6 [&::-webkit-slider-thumb]:bg-amber-400 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-lg`}
            style={{
              background: `linear-gradient(to right, rgb(251, 191, 36) ${lightPct}%, rgb(30, 41, 59) ${lightPct}%)`
            }}
          />
        </div>
      </div>
    </div>
  );
}
