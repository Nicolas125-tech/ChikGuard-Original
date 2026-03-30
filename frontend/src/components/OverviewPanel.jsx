import React, { useState, useEffect, useCallback } from 'react';
import { Thermometer, Bird, CheckCircle, LayoutDashboard, Wind, Zap, Maximize, WifiOff, AlertTriangle, ExternalLink } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { io } from 'socket.io-client';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import * as XLSX from 'xlsx';
import { getBaseUrl, isTunnelHost } from '../utils/config';
import WebRTCVideo from './WebRTCVideo';
import HeatmapOverlay from './HeatmapOverlay';

export default function OverviewPanel({ token, serverIP, prefs, canControlDevices }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(false);
  const [videoBlocked, setVideoBlocked] = useState(false);
  const [historico, setHistorico] = useState([]);
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [contagem, setContagem] = useState(0);
  const [showHeatmap24, setShowHeatmap24] = useState(false);
  const [carcass, setCarcass] = useState({ count: 0, audio_alert: false, items: [] });
  const [summary, setSummary] = useState(null);
  const [showHeatmapOverlay, setShowHeatmapOverlay] = useState(false);

  const baseUrl = getBaseUrl(serverIP);
  const videoUrl = `${baseUrl}/api/video`;
  const webrtcUrl = `${baseUrl}/api/webrtc/offer`;
  const heatmap24Url = `${baseUrl}/api/heatmap/rolling24/image?hours=24&t=${Date.now()}`;

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/status`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error();
      setDados(await r.json());
      setErro(false);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/history`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('History fetch failed');
      setHistorico(await r.json());
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchDevices = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Device state fetch failed');
      setDispositivos(await r.json());
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchCount = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/chick_count`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Count fetch failed');
      const data = await r.json();
      setContagem(data.count || 0);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchCarcassAndSummary = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([
        fetch(`${baseUrl}/api/carcass/live`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${baseUrl}/api/summary`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (c.ok) setCarcass(await c.json());
      if (s.ok) setSummary(await s.json());
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    fetchStatus(); fetchHistory(); fetchDevices(); fetchCount(); fetchCarcassAndSummary();
    const a = setInterval(fetchStatus, prefs.statusMs);
    const b = setInterval(fetchHistory, prefs.historyMs);
    const c = setInterval(fetchDevices, prefs.devicesMs);
    const d = setInterval(fetchCount, prefs.countMs);
    const e = setInterval(fetchCarcassAndSummary, prefs.statusMs);

    const socket = io(baseUrl);
    socket.on('new_alert', (data) => {
      console.log('Socket event received (OverviewPanel):', data);
      fetchStatus();
      fetchCount();
      fetchCarcassAndSummary();
      fetchHistory();
    });

    return () => {
      clearInterval(a); clearInterval(b); clearInterval(c); clearInterval(d); clearInterval(e);
      socket.disconnect();
    };
  }, [fetchStatus, fetchHistory, fetchDevices, fetchCount, fetchCarcassAndSummary, prefs, baseUrl]);

  const exportToPDF = async () => {
    const el = document.getElementById('overview-panel-content');
    if (!el) return;
    const canvas = await html2canvas(el, { scale: 1.5, useCORS: true });
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('l', 'pt', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    pdf.save(`relatorio-granja-${new Date().toISOString().slice(0,10)}.pdf`);
  };

  const exportToExcel = () => {
    const wb = XLSX.utils.book_new();
    const wsHistory = XLSX.utils.json_to_sheet(historico || []);
    XLSX.utils.book_append_sheet(wb, wsHistory, "Historico");

    const wsSummary = XLSX.utils.json_to_sheet([{
      Data: new Date().toISOString(),
      TemperaturaAtual: dados?.temperatura,
      ContagemAves: contagem,
      ComfortScore: summary?.comfort_score
    }]);
    XLSX.utils.book_append_sheet(wb, wsSummary, "Resumo");

    XLSX.writeFile(wb, `relatorio-granja-${new Date().toISOString().slice(0,10)}.xlsx`);
  };

  useEffect(() => {
    if (!carcass?.audio_alert) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);
      oscillator.type = 'square';
      oscillator.frequency.setValueAtTime(880, ctx.currentTime);
      gainNode.gain.setValueAtTime(0.001, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.08, ctx.currentTime + 0.02);
      oscillator.start();
      setTimeout(() => {
        oscillator.stop();
        ctx.close();
      }, 280);
    } catch (err) {
      console.debug('Audio error', err);
    }
  }, [carcass?.audio_alert, carcass?.count]);

  const toggleDevice = async (tipo, ligar) => {
    if (!canControlDevices) return;
    await fetch(`${baseUrl}/api/${tipo}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ligar }),
    });
    fetchDevices();
  };

  return (
    <div id="overview-panel-content" className="grid gap-6 grid-cols-1 lg:grid-cols-3 relative">
      <div className="flex sm:absolute sm:-top-16 sm:right-0 gap-3 z-10 mb-4 sm:mb-0">
        <button onClick={exportToPDF} className="flex-1 sm:flex-none justify-center bg-slate-800 border border-slate-700 hover:bg-slate-700 font-medium px-4 py-2 rounded-xl flex items-center gap-2 shadow-sm transition-colors text-sm text-slate-200">
          PDF
        </button>
        <button onClick={exportToExcel} className="flex-1 sm:flex-none justify-center bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/40 font-medium px-4 py-2 rounded-xl flex items-center gap-2 shadow-sm transition-colors text-sm">
          Excel
        </button>
      </div>

      <div className="lg:col-span-1 space-y-4 sm:space-y-6 flex flex-col">
        <div className="p-5 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400 font-semibold text-xs sm:text-sm uppercase tracking-widest mb-3 sm:mb-4">
            <Thermometer size={18} className="text-rose-400" /> Temperatura media
          </div>
          <div className="text-5xl sm:text-6xl font-black text-white mb-2 sm:mb-3 tracking-tighter drop-shadow-sm">{dados ? dados.temperatura : '--'} <span className="text-3xl sm:text-4xl text-slate-500 font-bold tracking-normal">°C</span></div>
          <div className="inline-flex px-3 py-1 sm:px-4 sm:py-1.5 rounded-lg font-bold text-xs sm:text-sm bg-slate-950/60 border border-white/5 shadow-inner text-slate-300">
            {erro ? 'SEM CONEXAO' : dados?.status || 'CARREGANDO'}
          </div>
        </div>

        <div className="p-5 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="flex justify-between items-start mb-3 sm:mb-4">
            <div className="flex items-center gap-2 text-slate-400 font-semibold text-xs sm:text-sm uppercase tracking-widest">
              <Bird size={18} className="text-indigo-400" /> Contagem
            </div>
            <CheckCircle className="text-emerald-500 drop-shadow-sm" size={20} />
          </div>
          <div className="text-5xl sm:text-6xl font-black text-white tracking-tighter drop-shadow-sm">{erro ? '--' : contagem} <span className="text-lg sm:text-xl text-slate-500 font-bold tracking-normal uppercase ml-1">aves</span></div>
        </div>

        <div className="p-5 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <h3 className="text-slate-400 text-xs sm:text-sm font-semibold uppercase mb-3 sm:mb-4 flex items-center gap-2 tracking-widest">
            <LayoutDashboard size={16} className="text-amber-400" /> Historico Termico
          </h3>
          <div className="h-[140px] sm:h-40 w-full -ml-4 sm:ml-0">
            {historico.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historico} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="hora" stroke="#64748b" fontSize={10} tickMargin={8} />
                  <YAxis domain={['dataMin - 2', 'dataMax + 2']} stroke="#64748b" fontSize={10} tickMargin={8} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} labelStyle={{ color: '#94a3b8', marginBottom: '4px' }} itemStyle={{ color: '#10b981', fontWeight: 'bold' }} />
                  <Line type="monotone" dataKey="temp" stroke="#10b981" strokeWidth={3} dot={{ fill: '#0f172a', stroke: '#10b981', strokeWidth: 2, r: 4 }} activeDot={{ r: 6, fill: '#10b981', stroke: '#fff' }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-slate-500 text-sm font-medium bg-slate-950/30 rounded-xl">Carregando grafico...</div>}
          </div>
        </div>

        <div className="p-5 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="grid grid-cols-2 gap-3 sm:gap-4 h-full">
            <button disabled={!canControlDevices} onClick={() => toggleDevice('ventilacao', !dispositivos.ventilacao)} className={`bg-slate-950 border p-4 sm:p-5 rounded-2xl flex flex-col items-center justify-center gap-3 transition-all ${dispositivos.ventilacao ? 'border-blue-500/50 bg-blue-500/10 shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-slate-800 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-1'}`}>
              <Wind size={28} className={dispositivos.ventilacao ? "text-blue-400" : "text-slate-500"} />
              <span className={`text-xs sm:text-sm font-bold tracking-wide uppercase ${dispositivos.ventilacao ? "text-blue-300" : "text-slate-400"}`}>Ventilar</span>
            </button>
            <button disabled={!canControlDevices} onClick={() => toggleDevice('aquecedor', !dispositivos.aquecedor)} className={`bg-slate-950 border p-4 sm:p-5 rounded-2xl flex flex-col items-center justify-center gap-3 transition-all ${dispositivos.aquecedor ? 'border-orange-500/50 bg-orange-500/10 shadow-[0_0_15px_rgba(249,115,22,0.15)]' : 'border-slate-800 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-1'}`}>
              <Zap size={28} className={dispositivos.aquecedor ? "text-orange-400" : "text-slate-500"} />
              <span className={`text-xs sm:text-sm font-bold tracking-wide uppercase ${dispositivos.aquecedor ? "text-orange-300" : "text-slate-400"}`}>Aquecer</span>
            </button>
          </div>
        </div>

        <div className="p-5 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="text-xs sm:text-sm uppercase font-semibold tracking-widest text-slate-400 mb-2">Score de Conforto</div>
          <div className="text-4xl sm:text-5xl font-black text-white drop-shadow-sm">{summary?.comfort_score ?? '--'}</div>
          <div className="w-full h-3 sm:h-4 bg-slate-950 rounded-full mt-4 overflow-hidden border border-slate-800/50 shadow-inner">
            <div
              className={`h-full transition-all duration-1000 ease-out ${Number(summary?.comfort_score || 0) >= 80 ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' : Number(summary?.comfort_score || 0) >= 60 ? 'bg-gradient-to-r from-yellow-500 to-amber-400' : 'bg-gradient-to-r from-red-600 to-rose-500'}`}
              style={{ width: `${Math.max(0, Math.min(100, Number(summary?.comfort_score || 0)))}%` }}
            />
          </div>
        </div>
      </div>

      <div className="lg:col-span-2 h-full">
        <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl sm:rounded-3xl overflow-hidden min-h-[350px] sm:min-h-[500px] h-full relative flex flex-col shadow-sm backdrop-blur-sm">
          <div className="p-3 sm:p-4 border-b border-slate-800/80 flex flex-col sm:flex-row justify-between items-start sm:items-center bg-slate-950/80 backdrop-blur-md absolute top-0 left-0 right-0 z-20 gap-3 sm:gap-0">
            <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm uppercase tracking-wider"><Maximize size={16} className="text-emerald-400" /> Transmissao da camera</h3>
            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              <button onClick={() => setShowHeatmapOverlay((v) => !v)} className="flex-1 sm:flex-none justify-center text-xs font-semibold bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 rounded-lg px-3 py-1.5 transition-colors">
                {showHeatmapOverlay ? 'Ocultar Heatmap' : 'Mostrar Heatmap'}
              </button>
              <button onClick={() => setShowHeatmap24((v) => !v)} className="flex-1 sm:flex-none justify-center text-xs font-semibold bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 rounded-lg px-3 py-1.5 transition-colors">
                {showHeatmap24 ? 'Mostrar Video' : 'Heatmap 24h'}
              </button>
            </div>
          </div>

          <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden h-full min-h-[350px] sm:min-h-[500px]">
            {erro ? (
              <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-950/50 absolute inset-0">
                <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 flex flex-col items-center">
                  <WifiOff size={40} className="text-slate-600 mb-4" />
                  <p className="text-slate-400 font-medium">Sem sinal de video</p>
                </div>
              </div>
            ) : videoBlocked ? (
              <img src={videoUrl} alt="Camera Fallback" className="absolute inset-0 w-full h-full object-contain z-0" />
            ) : showHeatmap24 ? (
              <img src={heatmap24Url} alt="Heatmap 24h" className="absolute inset-0 w-full h-full object-contain" />
            ) : (
              <>
                <WebRTCVideo url={webrtcUrl} token={token} className="absolute inset-0 w-full h-full object-contain z-0" onConnectionStateChange={(state) => { if(state === 'failed' || state === 'disconnected' || state === 'closed') { console.warn("WebRTC failed, falling back to MJPEG"); setVideoBlocked(true); } }} />
                {showHeatmapOverlay && <HeatmapOverlay serverIP={serverIP} />}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
