import React, { useState, useEffect, useCallback, useRef } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import SystemCard from './SystemCard';
import { getBaseUrl } from '../utils/config';
import { RefreshCw, Download } from 'lucide-react';

export default function ManagementPanel({ serverIP, prefs, token, cameras = [], activeCamera }) {
  const baseUrl = getBaseUrl(serverIP);
  const dadosRef = useRef(null);
  const [weightLive, setWeightLive] = useState(null);
  const [weightCurve, setWeightCurve] = useState([]);
  const [acoustic, setAcoustic] = useState(null);
  const [acousticModel, setAcousticModel] = useState(null);
  const [thermal, setThermal] = useState({ count: 0, sectors: [], items: [] });
  const [energy, setEnergy] = useState(null);
  const [audit, setAudit] = useState({ count: 0, items: [] });
  const [sync, setSync] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [audioMsg, setAudioMsg] = useState('');
  const [isClassifying, setIsClassifying] = useState(false);
  const [sensorHistory, setSensorHistory] = useState([]);
  const [weather, setWeather] = useState(null);
  const farmName = cameras.find(c => c.camera_id === activeCamera)?.name || 'Granja Principal';

  const loadManagement = useCallback(async () => {
    const headers = { Authorization: `Bearer ${token}` };
    const [wCurve, th, en, au, sy, sh, sum] = await Promise.all([
      fetch(`${baseUrl}/api/weight/curve?days=30`, { headers }),
      fetch(`${baseUrl}/api/thermal-anomalies/live?minutes=60`, { headers }),
      fetch(`${baseUrl}/api/energy/summary`, { headers }),
      fetch(`${baseUrl}/api/audit/logs?limit=80`, { headers }),
      fetch(`${baseUrl}/api/sync/status`, { headers }),
      fetch(`${baseUrl}/api/sensors/history?limit=120`, { headers }),
      fetch(`${baseUrl}/api/summary`, { headers }),
    ]);
    if (wCurve.ok) {
      const data = (await wCurve.json()).items || [];
      setWeightCurve(prev => JSON.stringify(prev) === JSON.stringify(data) ? prev : data);
    }
    if (th.ok) {
      const data = await th.json();
      setThermal(prev => JSON.stringify(prev) === JSON.stringify(data) ? prev : data);
    }
    if (en.ok) {
      const data = await en.json();
      setEnergy(prev => JSON.stringify(prev) === JSON.stringify(data) ? prev : data);
    }
    if (au.ok) {
      const data = await au.json();
      setAudit(prev => JSON.stringify(prev) === JSON.stringify(data) ? prev : data);
    }
    if (sy.ok) {
      const data = await sy.json();
      setSync(prev => JSON.stringify(prev) === JSON.stringify(data) ? prev : data);
    }
    if (sh.ok) {
      const data = (await sh.json()).items || [];
      setSensorHistory(prev => JSON.stringify(prev) === JSON.stringify(data) ? prev : data);
    }
    if (sum.ok) {
      const d = await sum.json();
      const prev = dadosRef.current;
      const newStr = JSON.stringify(d);
      if (!prev || JSON.stringify(prev) !== newStr) {
        setWeightLive(d.weight);
        setAcoustic(d.acoustic);
        setAcousticModel({ loaded: d.acoustic.trained_model_loaded });
        setWeather(d.weather);
        dadosRef.current = d;
      }
    }
  }, [baseUrl, token]);

  const classifyAudio = async () => {
    if (!audioFile) {
      setAudioMsg('Selecione um arquivo .wav');
      return;
    }
    const form = new FormData();
    form.append('audio', audioFile);
    setIsClassifying(true);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const r = await fetch(`${baseUrl}/api/acoustic/classify`, { method: 'POST', body: form, headers });
      const data = await r.json();
      if (!r.ok) {
        setAudioMsg(data.msg || 'Falha na classificação');
      } else {
        setAudioMsg(`Classificado. Cough index: ${data.result.cough_index}`);
        setAcoustic(data.result);
      }
    } catch {
      setAudioMsg('Erro ao classificar o áudio.');
    } finally {
      setIsClassifying(false);
    }
  };

  const exportWeightCurveToCSV = () => {
    if (!weightCurve || weightCurve.length === 0) return;
    const header = "Data,Peso Estimado (g),Peso Ideal (g)\n";
    const csvContent = weightCurve.map(row => `${row.timestamp},${row.avg_weight_g},${row.ideal_weight_g}`).join("\n");
    const blob = new Blob([header + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `curva_crescimento_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    const bootstrap = setTimeout(loadManagement, 0);
    const timer = setInterval(loadManagement, prefs.historyMs);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
    };
  }, [loadManagement, prefs.historyMs]);

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="mb-2">
        <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          Gestão Avançada - <span className="text-emerald-400">{farmName}</span>
        </h2>
        <p className="text-slate-400 text-sm mt-1">Dados de crescimento, financeiro e saúde avançada.</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <SystemCard label="Peso medio estimado" value={weightLive ? `${weightLive.avg_weight_g} g` : '--'} />
        <SystemCard label="Indice respiratorio" value={acoustic ? acoustic.respiratory_health_index : '--'} />
        <SystemCard label="Custo energia (mes)" value={energy ? `R$ ${energy.estimated_cost}` : '--'} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-lg sm:text-xl text-white tracking-tight flex items-center gap-2">
              <span className="bg-emerald-500/20 text-emerald-400 p-2 rounded-xl border border-emerald-500/30">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              </span>
              Curva de Crescimento
            </h3>
            {weightCurve.length > 0 && (
              <button 
                onClick={exportWeightCurveToCSV}
                className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 transition-colors"
                title="Baixar em Excel/CSV"
              >
                <Download size={14} /> Exportar
              </button>
            )}
          </div>
          <div className="h-64 sm:h-72 w-full -ml-4 sm:ml-0 bg-slate-950/40 rounded-xl border border-slate-800 p-2 sm:p-4 shadow-inner">
            {weightCurve.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weightCurve} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="timestamp" hide />
                  <YAxis stroke="#64748b" fontSize={10} tickMargin={8} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} labelStyle={{ color: '#94a3b8', marginBottom: '4px' }} />
                  <Line type="monotone" dataKey="avg_weight_g" name="Peso estimado (g)" stroke="#10b981" strokeWidth={3} dot={false} activeDot={{ r: 6, fill: '#10b981', stroke: '#fff' }} />
                  <Line type="monotone" dataKey="ideal_weight_g" name="Peso ideal (g)" stroke="#f59e0b" strokeWidth={3} strokeDasharray="5 5" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-slate-500 font-medium">Coletando dados...</div>}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
          <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight flex items-center gap-2">
            <span className="bg-purple-500/20 text-purple-400 p-2 rounded-xl border border-purple-500/30">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/><line x1="8" x2="16" y1="22" y2="22"/></svg>
            </span>
            Saúde Respiratória (IA)
          </h3>
          <div className="space-y-3 text-xs sm:text-sm">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-1 hover:border-slate-700 transition-colors">
                <span className="text-slate-500 font-medium">Índice Geral</span>
                <span className="text-xl sm:text-2xl font-bold text-emerald-400">{acoustic?.respiratory_health_index ?? '--'}</span>
              </div>
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-1 hover:border-slate-700 transition-colors">
                <span className="text-slate-500 font-medium">Tosse Detec.</span>
                <span className="text-xl sm:text-2xl font-bold text-amber-400">{acoustic?.cough_index ?? '--'}</span>
              </div>
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-1 hover:border-slate-700 transition-colors">
                <span className="text-slate-500 font-medium">Estresse Sonoro</span>
                <span className="text-xl sm:text-2xl font-bold text-rose-400">{acoustic?.stress_audio_index ?? '--'}</span>
              </div>
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-1 hover:border-slate-700 transition-colors justify-center items-center">
                <span className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${acousticModel?.loaded ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/20 text-red-400 border border-red-500/20'}`}>
                  {acousticModel?.loaded ? 'Modelo Ativo' : 'Modelo Offline'}
                </span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 sm:p-5 mt-4">
              <span className="block text-slate-400 font-medium mb-3 text-sm">Classificação Manual (.wav)</span>
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                  <input aria-label="Upload de arquivo de áudio WAV para classificação manual" type="file" accept=".wav,audio/wav" disabled={isClassifying} onChange={(e) => setAudioFile(e.target.files?.[0] || null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10 disabled:cursor-not-allowed" />
                  <div className={`bg-slate-900 border border-slate-700 border-dashed rounded-lg px-4 py-2.5 text-center text-slate-300 hover:bg-slate-800 hover:border-slate-600 transition-all ${isClassifying ? 'opacity-50' : ''}`}>
                    {audioFile ? <span className="text-emerald-400 font-medium">{audioFile.name}</span> : 'Selecionar arquivo de áudio'}
                  </div>
                </div>
                <button onClick={classifyAudio} disabled={!audioFile || isClassifying} className="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-lg font-bold shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap">
                  {isClassifying ? <RefreshCw size={16} className="animate-spin" /> : 'Analisar'}
                </button>
              </div>
              {audioMsg && <div className="mt-3 text-sm font-medium text-amber-400 bg-amber-500/10 p-2 rounded-lg border border-amber-500/20 text-center">{audioMsg}</div>}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-lg sm:text-xl text-white tracking-tight flex items-center gap-2">
              <span className="bg-rose-500/20 text-rose-400 p-2 rounded-xl border border-rose-500/30">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m13.4 2-8.3 8.3a2 2 0 0 0 0 2.8l7.1 7.1a2 2 0 0 0 2.8 0l8.3-8.3v-6a2 2 0 0 0-2-2h-6z"/><path d="M16 6h.01"/></svg>
              </span>
              Anomalias Térmicas
            </h3>
            <span className="bg-rose-500 text-white font-bold px-3 py-1 rounded-full text-sm shadow-md">{thermal.count || 0}</span>
          </div>
          <p className="text-sm text-slate-400 mb-4 bg-slate-950/60 p-3 rounded-xl border border-slate-800 flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500"><path d="m21.21 15.89-9-13a2 2 0 0 0-3.32 0l-9 13a2 2 0 0 0 1.66 3.1h18.66a2 2 0 0 0 1.66-3.1z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
            Setores afetados: <span className="font-semibold text-slate-300">{(thermal.sectors || []).join(', ') || 'Nenhum'}</span>
          </p>
          <div className="max-h-60 overflow-y-auto space-y-2 pr-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {(thermal.items || []).slice(0, 20).map((item) => (
              <div key={item.id} className="bg-slate-950/60 border border-slate-800/80 rounded-xl px-4 py-3 text-sm flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 hover:bg-slate-800/30 transition-colors">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${item.kind === 'hot' ? 'bg-rose-500' : 'bg-blue-500'}`}></span>
                  <span className="font-mono text-slate-400">UID {item.bird_uid}</span>
                </div>
                <span className="font-bold text-white text-lg">{item.estimated_temp_c}°C</span>
                <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider bg-slate-900 px-2.5 py-1 rounded border border-slate-800">Setor {item.sector}</span>
              </div>
            ))}
            {(thermal.items || []).length === 0 && <div className="text-slate-500 text-sm text-center py-6">Nenhuma anomalia detectada recentemente.</div>}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
          <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight flex items-center gap-2">
            <span className="bg-blue-500/20 text-blue-400 p-2 rounded-xl border border-blue-500/30">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
            </span>
            Financeiro e Sync
          </h3>
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-1">
                <span className="text-slate-500 font-medium">Consumo Est.</span>
                <span className="text-xl font-bold text-cyan-400">{energy?.total_kwh ?? '--'} kWh</span>
              </div>
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-1">
                <span className="text-slate-500 font-medium">Custo Mês</span>
                <span className="text-xl font-bold text-rose-400">{energy ? `R$ ${energy.estimated_cost}` : '--'}</span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex items-start gap-3">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-400 flex-shrink-0 mt-0.5"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
              <div>
                <span className="block font-semibold text-slate-300 mb-1">Sugestão de Economia</span>
                <span className="text-slate-400 leading-relaxed">{energy?.suggestion || 'Nenhuma sugestão no momento.'}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex justify-between items-center">
                <span className="text-slate-400 font-medium">Sync Nuvem</span>
                <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wider ${sync?.cloud_sync_url_configured ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>{sync?.cloud_sync_url_configured ? 'ON' : 'OFF'}</span>
              </div>
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex justify-between items-center">
                <span className="text-slate-400 font-medium">Pendências</span>
                <span className="font-bold text-white bg-slate-800 px-2 py-1 rounded">{sync?.pending ?? '--'}</span>
              </div>
            </div>

            <div className={`border rounded-xl p-4 shadow-inner ${weather?.preheat_recommended ? 'bg-blue-600/10 border-blue-500/30' : 'bg-slate-950/60 border-slate-800'}`}>
              <div className="flex items-center gap-2 mb-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={weather?.preheat_recommended ? 'text-blue-400' : 'text-slate-500'}><path d="M17.5 19C19.5 19 21 17.5 21 15.5C21 13.5 19.5 12 17.5 12C16.8 12 16.1 12.2 15.6 12.6C15.2 10.5 13.5 9 11.5 9C9.3 9 7.5 10.8 7.5 13C7.5 13.2 7.5 13.5 7.6 13.7C5.6 13.8 4 15.4 4 17.5C4 19.5 5.5 21 7.5 21H17.5Z"/></svg>
                <span className={`font-semibold ${weather?.preheat_recommended ? 'text-blue-300' : 'text-slate-300'}`}>Previsão Climática</span>
              </div>
              <span className="text-slate-400 leading-relaxed">{weather?.message || 'Dados indisponíveis.'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
        <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight">Nível de Ração (Silagem)</h3>
        <div className="h-56 sm:h-64 bg-slate-950/40 rounded-xl border border-slate-800 p-2 sm:p-4 shadow-inner">
          {sensorHistory.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sensorHistory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="timestamp" hide />
                <YAxis stroke="#64748b" fontSize={10} domain={[0, 100]} tickMargin={8} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} labelStyle={{ color: '#94a3b8', marginBottom: '4px' }} formatter={(value) => [`${value}%`, 'Nível']} />
                <Line type="monotone" dataKey="feed_level_pct" stroke="#38bdf8" strokeWidth={3} dot={false} activeDot={{ r: 6, fill: '#38bdf8', stroke: '#fff' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <div className="h-full flex items-center justify-center text-slate-500 font-medium">Sem dados de ração.</div>}
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm">
        <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight flex items-center gap-2">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          Audit Trail
        </h3>
        <div className="bg-slate-950/40 rounded-xl border border-slate-800 overflow-hidden">
          <div className="max-h-80 overflow-y-auto p-2 space-y-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {(audit.items || []).slice(0, 100).map((item) => (
              <div key={item.id} className="bg-slate-900 border border-slate-800/80 rounded-lg px-4 py-3 text-xs sm:text-sm flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 hover:bg-slate-800/50 transition-colors">
                <span className="text-slate-500 font-mono whitespace-nowrap">{item.timestamp}</span>
                <span className="font-bold text-slate-300 w-24 truncate" title={item.actor}>{item.actor}</span>
                <span className="text-slate-400 flex-1">{item.action}</span>
              </div>
            ))}
            {(audit.items || []).length === 0 && <div className="text-slate-500 text-sm text-center py-6">Nenhum evento registrado.</div>}
          </div>
        </div>
      </div>
      
      {/* Calculadoras Inseridas para o cliente final */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
        <CalculadoraCA />
        <CalculadoraLucro />
      </div>
      
      
    </div>
  );
}

// Bolt Optimization: Memoize CalculadoraCA to prevent unnecessary re-renders when ManagementPanel polls
const CalculadoraCA = React.memo(function CalculadoraCA() {
  const [racao, setRacao] = useState('');
  const [peso, setPeso] = useState('');
  
  const ca = (Number(racao) > 0 && Number(peso) > 0) ? (Number(racao) / Number(peso)).toFixed(2) : '--';
  let avaliacao = "Aguardando dados...";
  let color = "text-slate-400";
  
  if (ca !== '--') {
    const val = Number(ca);
    if (val < 1.5) { avaliacao = "Excelente"; color = "text-emerald-400"; }
    else if (val <= 1.7) { avaliacao = "Bom"; color = "text-blue-400"; }
    else if (val <= 1.9) { avaliacao = "Atenção"; color = "text-amber-400"; }
    else { avaliacao = "Ruim - Desperdício"; color = "text-rose-400"; }
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none"></div>
      
      <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight flex items-center gap-2">
        <span className="bg-indigo-500/20 text-indigo-400 p-2 rounded-xl border border-indigo-500/30">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 22h14a2 2 0 0 0 2-2V7.5L14.5 2H6a2 2 0 0 0-2 2v4"/><polyline points="14 2 14 8 20 8"/><path d="m3 15 4 4 4-4"/><path d="M7 11v8"/></svg>
        </span>
        Calculadora Rápida: Conversão Alimentar (CA)
      </h3>
      <p className="text-slate-400 text-sm mb-4">A conversão alimentar indica quantos quilos de ração são necessários para produzir 1 quilo de frango. Quanto menor o índice, melhor.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-950/60 p-4 sm:p-5 rounded-xl border border-slate-800 shadow-inner">
          <label className="text-xs text-slate-400 uppercase tracking-wider font-bold mb-2 block">Ração Consumida (kg)</label>
          <input 
            type="number" 
            value={racao} 
            onChange={e=>setRacao(e.target.value)} 
            placeholder="Ex: 5000" 
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white font-mono text-lg outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-slate-600" 
          />
        </div>
        <div className="bg-slate-950/60 p-4 sm:p-5 rounded-xl border border-slate-800 shadow-inner">
          <label className="text-xs text-slate-400 uppercase tracking-wider font-bold mb-2 block">Peso Total do Lote (kg)</label>
          <input 
            type="number" 
            value={peso} 
            onChange={e=>setPeso(e.target.value)} 
            placeholder="Ex: 3100" 
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white font-mono text-lg outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-slate-600" 
          />
        </div>
        <div className="bg-slate-800 p-4 sm:p-5 rounded-xl border border-slate-700 flex flex-col justify-center items-center shadow-md relative overflow-hidden">
          <div className={`absolute top-0 right-0 w-full h-full opacity-5 pointer-events-none ${ca !== '--' ? color.replace('text', 'bg') : ''}`}></div>
          <span className="text-xs text-slate-300 uppercase tracking-wider font-bold mb-1 z-10">Resultado (CA)</span>
          <span className={`text-4xl sm:text-5xl font-black z-10 ${color}`}>{ca}</span>
          <span className={`text-sm font-bold mt-2 px-3 py-1 bg-slate-900/50 rounded-full border border-slate-700 z-10 ${color}`}>{avaliacao}</span>
        </div>
      </div>
    </div>
  );
});

// Bolt Optimization: Memoize CalculadoraLucro to prevent unnecessary re-renders when ManagementPanel polls
const CalculadoraLucro = React.memo(function CalculadoraLucro() {
  const [lote, setLote] = useState('');
  const [mortalidade, setMortalidade] = useState('');
  const [pesoAbate, setPesoAbate] = useState('');
  const [precoKg, setPrecoKg] = useState('');
  
  const avesFinais = Number(lote) > 0 ? (Number(lote) * (1 - (Number(mortalidade) / 100))) : 0;
  const pesoTotal = avesFinais * Number(pesoAbate);
  const receita = pesoTotal * Number(precoKg);

  const formatBRL = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-sm relative overflow-hidden flex flex-col h-full">
      <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>
      
      <h3 className="font-bold text-lg sm:text-xl text-white mb-4 tracking-tight flex items-center gap-2">
        <span className="bg-emerald-500/20 text-emerald-400 p-2 rounded-xl border border-emerald-500/30">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
        </span>
        Simulador de Receita Bruta
      </h3>
      <p className="text-slate-400 text-sm mb-4">Projete seus ganhos reais do lote no fechamento.</p>
      
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
          <label className="text-[10px] text-slate-400 uppercase font-bold mb-1 block">Qtd de Aves</label>
          <input type="number" value={lote} onChange={e=>setLote(e.target.value)} placeholder="Ex: 30000" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono text-sm outline-none focus:border-emerald-500" />
        </div>
        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
          <label className="text-[10px] text-slate-400 uppercase font-bold mb-1 block">Mortalidade (%)</label>
          <input type="number" value={mortalidade} onChange={e=>setMortalidade(e.target.value)} placeholder="Ex: 3.5" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono text-sm outline-none focus:border-emerald-500" />
        </div>
        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
          <label className="text-[10px] text-slate-400 uppercase font-bold mb-1 block">Peso Abate (kg)</label>
          <input type="number" value={pesoAbate} onChange={e=>setPesoAbate(e.target.value)} placeholder="Ex: 2.9" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono text-sm outline-none focus:border-emerald-500" />
        </div>
        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
          <label className="text-[10px] text-slate-400 uppercase font-bold mb-1 block">R$/kg de Carne</label>
          <input type="number" value={precoKg} onChange={e=>setPrecoKg(e.target.value)} placeholder="Ex: 5.50" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono text-sm outline-none focus:border-emerald-500" />
        </div>
      </div>
      
      <div className="bg-slate-800 mt-auto p-4 rounded-xl border border-emerald-500/30 flex justify-between items-center shadow-md shadow-emerald-500/5">
        <span className="text-xs text-slate-300 uppercase tracking-wider font-bold">Receita Bruta Est.</span>
        <span className="text-2xl font-black text-emerald-400">{receita > 0 ? formatBRL(receita) : 'R$ 0,00'}</span>
      </div>
    </div>
  );
});
