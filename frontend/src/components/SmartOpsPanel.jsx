import React, { useState, useEffect, useCallback } from 'react';
import SystemCard from './SystemCard';
import { getBaseUrl } from '../utils/config';

export default function SmartOpsPanel({ serverIP, prefs, token }) {
  const baseUrl = getBaseUrl(serverIP);
  const [behavior, setBehavior] = useState(null);
  const [immobility, setImmobility] = useState({ count: 0, items: [] });
  const [sensors, setSensors] = useState(null);
  const [autoMode, setAutoMode] = useState(null);
  const [batches, setBatches] = useState({ count: 0, items: [] });
  const [cameras, setCameras] = useState({ active_camera_id: '', items: [] });
  const [reportMsg, setReportMsg] = useState('');
  const [batchForm, setBatchForm] = useState({ name: '', start_date: '' });
  const [logbook, setLogbook] = useState({ count: 0, items: [] });
  const [logNote, setLogNote] = useState('');

  const heatmapUrl = `${baseUrl}/api/heatmap/daily/image`;

  const loadData = useCallback(async () => {
    const [b, i, s, a, bt, c, lb] = await Promise.all([
      fetch(`${baseUrl}/api/behavior/live`),
      fetch(`${baseUrl}/api/immobility/live`),
      fetch(`${baseUrl}/api/sensors/live`),
      fetch(`${baseUrl}/api/auto-mode`),
      fetch(`${baseUrl}/api/batches`),
      fetch(`${baseUrl}/api/cameras`),
      fetch(`${baseUrl}/api/logbook?limit=30`),
    ]);
    if (b.ok) setBehavior(await b.json());
    if (i.ok) setImmobility(await i.json());
    if (s.ok) setSensors(await s.json());
    if (a.ok) setAutoMode(await a.json());
    if (bt.ok) setBatches(await bt.json());
    if (c.ok) setCameras(await c.json());
    if (lb.ok) setLogbook(await lb.json());
  }, [baseUrl]);

  useEffect(() => {
    const bootstrap = setTimeout(loadData, 0);
    const timer = setInterval(loadData, prefs.statusMs);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
    };
  }, [loadData, prefs.statusMs]);

  const toggleAuto = async () => {
    await fetch(`${baseUrl}/api/auto-mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ enabled: !autoMode?.enabled }),
    });
    loadData();
  };

  const createBatch = async () => {
    if (!batchForm.name || !batchForm.start_date) return;
    await fetch(`${baseUrl}/api/batches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...batchForm, active: true }),
    });
    setBatchForm({ name: '', start_date: '' });
    loadData();
  };

  const generateWeeklyReport = async () => {
    const r = await fetch(`${baseUrl}/api/reports/weekly`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
    const data = await r.json();
    setReportMsg(r.ok ? `Relatorio gerado: ${data.file}` : (data.msg || 'Falha ao gerar relatorio'));
  };

  const saveLogNote = async () => {
    if (!logNote.trim()) return;
    await fetch(`${baseUrl}/api/logbook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: logNote, author: 'tratador' }),
    });
    setLogNote('');
    loadData();
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <SystemCard label="Comportamento" value={behavior?.status || '--'} />
        <SystemCard label="Imobilidade" value={immobility?.count ?? '--'} />
        <SystemCard label="Modo automatico" value={autoMode?.enabled ? 'Ativo' : 'Inativo'} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
          <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight flex items-center gap-2">
            <span className="bg-blue-500/20 text-blue-400 p-2 rounded-xl border border-blue-500/30">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            </span>
            Sensores IoT & Clima
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4 text-xs sm:text-sm">
            <div className="bg-slate-950/60 rounded-xl border border-slate-800 p-3 sm:p-4 hover:border-slate-600 transition-colors">
              <span className="text-slate-500 font-medium block mb-1">Temperatura</span>
              <span className="text-xl sm:text-2xl font-bold text-white">{sensors?.temperature_c ?? '--'} <span className="text-sm text-slate-400">°C</span></span>
            </div>
            <div className="bg-slate-950/60 rounded-xl border border-slate-800 p-3 sm:p-4 hover:border-slate-600 transition-colors">
              <span className="text-slate-500 font-medium block mb-1">Umidade</span>
              <span className="text-xl sm:text-2xl font-bold text-blue-300">{sensors?.humidity_pct ?? '--'} <span className="text-sm text-slate-400">%</span></span>
            </div>
            <div className="bg-slate-950/60 rounded-xl border border-slate-800 p-3 sm:p-4 hover:border-slate-600 transition-colors">
              <span className="text-slate-500 font-medium block mb-1">Amônia</span>
              <span className="text-xl sm:text-2xl font-bold text-amber-300">{sensors?.ammonia_ppm ?? '--'} <span className="text-sm text-slate-400">ppm</span></span>
            </div>
            <div className="bg-slate-950/60 rounded-xl border border-slate-800 p-3 sm:p-4 hover:border-slate-600 transition-colors">
              <span className="text-slate-500 font-medium block mb-1">Ração</span>
              <span className="text-xl sm:text-2xl font-bold text-emerald-300">{sensors?.feed_level_pct ?? '--'} <span className="text-sm text-slate-400">%</span></span>
            </div>
            <div className="bg-slate-950/60 rounded-xl border border-slate-800 p-3 sm:p-4 hover:border-slate-600 transition-colors">
              <span className="text-slate-500 font-medium block mb-1">Água</span>
              <span className="text-xl sm:text-2xl font-bold text-cyan-300">{sensors?.water_level_pct ?? '--'} <span className="text-sm text-slate-400">%</span></span>
            </div>
            <button onClick={toggleAuto} className={`rounded-xl p-3 sm:p-4 font-bold text-sm sm:text-base flex flex-col items-center justify-center gap-1 sm:gap-2 border transition-all ${autoMode?.enabled ? 'bg-emerald-600 border-emerald-500 text-white shadow-lg shadow-emerald-500/20' : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'}`}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={autoMode?.enabled ? 'text-white' : 'text-slate-400'}><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
              {autoMode?.enabled ? 'Auto Ativo' : 'Ativar Auto'}
            </button>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
          <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight">Heatmap Diário</h3>
          <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950 h-48 sm:h-64 flex items-center justify-center relative shadow-inner">
            <img src={heatmapUrl} alt="Heatmap diario" className="absolute inset-0 w-full h-full object-cover mix-blend-screen opacity-90" />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 to-transparent pointer-events-none" />
            <span className="absolute bottom-3 left-3 text-xs font-semibold text-slate-400 bg-slate-900/80 px-2 py-1 rounded-md backdrop-blur-sm">Acumulado 24h</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
          <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight flex items-center gap-2">
            Gestão de Lotes
          </h3>
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 mb-4">
            <input value={batchForm.name} onChange={(e) => setBatchForm((p) => ({ ...p, name: e.target.value }))} placeholder="Nome do lote (ex: Lote B)" className="flex-1 bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-2.5 text-sm sm:text-base focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all placeholder:text-slate-600" />
            <input type="date" value={batchForm.start_date} onChange={(e) => setBatchForm((p) => ({ ...p, start_date: e.target.value }))} className="flex-1 sm:w-auto bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-2.5 text-sm sm:text-base focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all text-slate-300" />
            <button onClick={createBatch} className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-5 py-2.5 font-bold shadow-lg shadow-blue-500/20 transition-all text-sm sm:text-base hover:-translate-y-0.5 whitespace-nowrap">
              + Novo
            </button>
          </div>
          <div className="max-h-48 overflow-y-auto space-y-2 pr-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {batches.items?.map((item) => (
              <div key={item.id} className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 sm:p-4 text-xs sm:text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-slate-800/30 transition-colors">
                <span className="font-semibold text-slate-200">{item.name}</span>
                <span className="text-slate-400">Início: <span className="text-slate-300">{item.start_date}</span></span>
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${item.active ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-500 border border-slate-700'}`}>
                  {item.active ? 'Ativo' : 'Concluído'}
                </span>
              </div>
            ))}
            {batches.items?.length === 0 && <div className="text-slate-500 text-sm text-center py-6">Nenhum lote registrado.</div>}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight">Infraestrutura</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-1">
                <span className="text-slate-500 text-xs sm:text-sm font-medium">Câmera Ativa</span>
                <span className="text-slate-200 font-bold truncate">{cameras.active_camera_id || 'Não configurada'}</span>
              </div>
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-1">
                <span className="text-slate-500 text-xs sm:text-sm font-medium">Total de Câmeras</span>
                <span className="text-slate-200 font-bold">{cameras.items?.length ?? 0}</span>
              </div>
            </div>
          </div>
          <div className="bg-slate-950/50 p-4 sm:p-5 rounded-2xl border border-slate-800">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4">
              <div className="text-sm">
                <span className="block font-semibold text-white mb-1">Relatórios Periódicos</span>
                <span className="text-slate-400 text-xs">Gere um consolidado em PDF com gráficos semanais.</span>
              </div>
              <button onClick={generateWeeklyReport} className="w-full sm:w-auto bg-amber-600 hover:bg-amber-500 text-white rounded-xl px-5 py-3 font-bold shadow-lg shadow-amber-500/20 transition-all text-sm hover:-translate-y-0.5">
                Gerar PDF Semanal
              </button>
            </div>
            {reportMsg && <div className="mt-3 text-sm font-medium text-emerald-400 bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20 text-center">{reportMsg}</div>}
          </div>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
        <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight flex items-center gap-2">
          Diário do Lote (Logbook)
        </h3>
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 mb-5">
          <input value={logNote} onChange={(e) => setLogNote(e.target.value)} placeholder="Descreva eventos importantes (ex: Dia 12: Vacinação Gumboro via água)..." className="flex-1 bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 text-sm sm:text-base focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all placeholder:text-slate-600" />
          <button onClick={saveLogNote} className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl px-6 py-3 text-sm sm:text-base font-bold shadow-lg shadow-emerald-500/20 transition-all hover:-translate-y-0.5 whitespace-nowrap">
            Registrar Log
          </button>
        </div>
        <div className="bg-slate-950/40 rounded-xl border border-slate-800 overflow-hidden">
          <div className="max-h-60 overflow-y-auto p-2 space-y-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {(logbook.items || []).map((item) => (
              <div key={item.id} className="bg-slate-900 border border-slate-800/80 rounded-lg px-4 py-3 text-xs sm:text-sm hover:border-slate-700 transition-colors">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-slate-500 font-mono text-xs">{item.timestamp}</span>
                  <span className="text-emerald-400 font-semibold text-xs uppercase bg-emerald-500/10 px-2 py-0.5 rounded">{item.author}</span>
                </div>
                <p className="text-slate-300 font-medium leading-relaxed">{item.note}</p>
              </div>
            ))}
            {(logbook.items || []).length === 0 && <div className="text-slate-500 text-sm text-center py-8">Nenhum log registrado. Comece a documentar o manejo.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
