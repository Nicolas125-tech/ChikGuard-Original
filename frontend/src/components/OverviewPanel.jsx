import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Thermometer, Bird, Activity, TrendingUp, TrendingDown, Minus, Database } from 'lucide-react';
import { getBaseUrl } from '@/utils/config';
import WeightForecastChart from '@/components/WeightForecastChart';
import QueryErrorState from './QueryErrorState';

/* ── Animated Number ─────────────────────────────────────────── */
const AnimatedNum = React.memo(function AnimatedNum({ value, decimals = 0 }) {
  const [display, setDisplay] = useState(value);
  const prev = useRef(value);

  useEffect(() => {
    if (value === null || value === undefined) return;
    const from = prev.current ?? 0;
    const to = Number(value);
    prev.current = to;
    if (isNaN(to)) {
      setTimeout(() => setDisplay(value), 0);
      return;
    }

    const duration = 600;
    const start = performance.now();
    const animate = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = from + (to - from) * eased;
      const displayVal = decimals > 0 
        ? Number(current).toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) 
        : Math.round(current).toLocaleString('pt-BR');
      setDisplay(displayVal);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [value, decimals]);

  return <>{display ?? '--'}</>;
});

/* ── Score Ring (SVG mini gauge) ──────────────────────────────── */
const ScoreRing = React.memo(function ScoreRing({ score, size = 100 }) {
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const s = Number(score) || 0;
  const offset = circumference - (s / 100) * circumference;
  const color = s >= 80 ? '#10b981' : s >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <svg width={size} height={size} className="drop-shadow-md">
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="hsl(222 38% 16%)" strokeWidth="6" />
      <circle
        cx={size/2} cy={size/2} r={radius} fill="none"
        stroke={color} strokeWidth="6" strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={offset}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)' }}
      />
      <text x="50%" y="50%" textAnchor="middle" dy="0.35em" fill="white" fontSize="22" fontWeight="800">
        {s}
      </text>
    </svg>
  );
});

export default function OverviewPanel({ token, serverIP, prefs, cameras = [], activeCamera, onTabChange }) {
  const [dados, setDados] = useState(null);
  const [contagem, setContagem] = useState(null);
  const [summary, setSummary] = useState(null);
  const [prevTemp, setPrevTemp] = useState(null);
  const [error, setError] = useState(null);
  const dadosRef = useRef(null);
  const baseUrl = getBaseUrl(serverIP);

  const fetchSummary = useCallback(async () => {
    try {
      setError(null);
      const r = await fetch(`${baseUrl}/api/summary`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) {
        const d = await r.json();
        setSummary(d);

        // Bolt Optimization: Reuse summary data to reduce API calls
        // Consolidates overlapping requests (/api/summary and /api/chick_count),
        // reducing network connections, database load, and React re-renders.
        const newTemp = d.temperatura_atual;
        const newStatus = d.status_atual;
        setContagem(d.contagem_aves);

        const prev = dadosRef.current;
        // Always update prevTemp to previous temp on every poll to reset trend
        setPrevTemp(prev?.temperatura ?? null);

        const newDados = { temperatura: newTemp, status: newStatus };
        setDados(newDados);
        dadosRef.current = newDados;
      } else {
        throw new Error('Falha ao carregar dados');
      }
    } catch (_e) { 
      console.error(_e); 
      setError(_e.message);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    (async () => { fetchSummary(); })();
    const c = setInterval(fetchSummary, prefs.statusMs);
    return () => {
        clearInterval(c);
    };
  }, [fetchSummary, prefs]);

  const temp = dados?.temperatura;
  const tempTrend = prevTemp !== null && temp !== null
    ? (temp > prevTemp ? 'up' : temp < prevTemp ? 'down' : 'stable')
    : null;

  const { onlineFarms, offlineFarms, activeCameraName } = useMemo(() => {
    const online = cameras.filter(c => c.status === 'online').length;
    const offline = cameras.length - online;
    const name = cameras.find(c => c.camera_id === activeCamera)?.name || 'Granja Principal';
    return { onlineFarms: online, offlineFarms: offline, activeCameraName: name };
  }, [cameras, activeCamera]);

  if (error) {
    return (
      <div className="space-y-6">
        <div className="mb-2">
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Visão Geral - <span className="text-emerald-400">{activeCameraName}</span>
          </h2>
          <p className="text-slate-400 text-sm mt-1">Monitoramento de telemetria e visão computacional em tempo real.</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-12 flex items-center justify-center min-h-[400px]">
          <QueryErrorState message={error} onRetry={fetchSummary} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          Visão Geral - <span className="text-emerald-400">{activeCameraName}</span>
        </h2>
        <p className="text-slate-400 text-sm mt-1">Monitoramento de telemetria e visão computacional em tempo real.</p>
      </div>

      {cameras.length > 1 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in-down mb-6">
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-2xl p-4 flex items-center justify-between shadow-lg">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-1">Total Granjas</p>
              <p className="text-3xl font-black text-white">{cameras.length}</p>
            </div>
            <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/50 shadow-inner">
              <Database className="text-slate-400" size={20} />
            </div>
          </div>
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-2xl p-4 flex items-center justify-between shadow-lg">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-1">Online</p>
              <p className="text-3xl font-black text-emerald-400">{onlineFarms}</p>
            </div>
            <div className="bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20 shadow-inner">
              <Activity className="text-emerald-400" size={20} />
            </div>
          </div>
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-2xl p-4 flex items-center justify-between shadow-lg">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-1">Offline</p>
              <p className={`text-3xl font-black ${offlineFarms > 0 ? 'text-rose-400' : 'text-slate-300'}`}>{offlineFarms}</p>
            </div>
            <div className={`${offlineFarms > 0 ? 'bg-rose-500/10 border-rose-500/20' : 'bg-slate-800/80 border-slate-700/50'} p-3 rounded-xl border shadow-inner`}>
              <Minus className={offlineFarms > 0 ? 'text-rose-400' : 'text-slate-400'} size={20} />
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-5 grid-cols-1 md:grid-cols-3">
      {/* ── Temperatura ── */}
      <div 
        onClick={() => onTabChange && onTabChange('climate')}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onTabChange && onTabChange('climate');
          }
        }}
        className="card-premium p-6 animate-fade-in-up stagger-1 hover-lift cursor-pointer hover:border-rose-500/40 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
        role="button" aria-label="Abrir painel de clima"
        tabIndex={0}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-slate-400 font-semibold text-xs uppercase tracking-widest">
            <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
              <Thermometer size={16} className="text-rose-400" />
            </div>
            Temperatura
          </div>
          {tempTrend && (
            <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-lg ${
              tempTrend === 'up' ? 'text-rose-400 bg-rose-500/10' :
              tempTrend === 'down' ? 'text-blue-400 bg-blue-500/10' :
              'text-slate-400 bg-slate-800'
            }`}>
              {tempTrend === 'up' ? <TrendingUp size={12}/> : tempTrend === 'down' ? <TrendingDown size={12}/> : <Minus size={12}/>}
              {tempTrend === 'up' ? 'Subindo' : tempTrend === 'down' ? 'Caindo' : 'Estável'}
            </div>
          )}
        </div>
        <div className="text-5xl font-black text-white mb-3 tracking-tighter">
          <AnimatedNum value={temp} decimals={1} /> <span className="text-3xl text-slate-500 font-bold">°C</span>
        </div>
        <div className="inline-flex px-3 py-1.5 rounded-lg font-semibold text-xs bg-slate-950/60 border border-slate-800/50 text-slate-400">
          {dados?.status || 'Aguardando Conexão'}
        </div>
      </div>

      {/* ── Detecções ── */}
      <div 
        onClick={() => onTabChange && onTabChange('birds')}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onTabChange && onTabChange('birds');
          }
        }}
        className="card-premium p-6 animate-fade-in-up stagger-2 hover-lift cursor-pointer hover:border-indigo-500/40 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
        role="button" aria-label="Abrir painel de aves"
        tabIndex={0}
      >
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center gap-2 text-slate-400 font-semibold text-xs uppercase tracking-widest">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
              <Bird size={16} className="text-indigo-400" />
            </div>
            Detecções IA
          </div>
          <div className="status-dot online" />
        </div>
        <div className="text-5xl font-black text-white tracking-tighter animate-count-up">
          <AnimatedNum value={contagem} /> <span className="text-lg text-slate-500 font-bold uppercase ml-1">aves</span>
        </div>
        <div className="mt-4 flex gap-2">
          <span className="text-xs font-medium text-slate-500 bg-slate-950/60 px-2.5 py-1 rounded-lg border border-slate-800/50">
            YOLO v8 • ByteTrack
          </span>
        </div>
      </div>

      {/* ── Score de Conforto ── */}
      <div 
        onClick={() => onTabChange && onTabChange('digitaltwin')}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onTabChange && onTabChange('digitaltwin');
          }
        }}
        className="card-premium p-6 animate-fade-in-up stagger-3 hover-lift cursor-pointer hover:border-emerald-500/40 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
        role="button" aria-label="Abrir painel do gêmeo digital"
        tabIndex={0}
      >
        <div className="text-xs uppercase font-semibold tracking-widest text-slate-400 mb-4 flex items-center gap-2">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
            <Activity size={16} className="text-emerald-400"/>
          </div>
          Score de Conforto
        </div>

        <div className="flex items-center gap-5">
          <ScoreRing score={summary?.comfort_score ?? 0} size={90} />
          <div>
            <div className="text-3xl font-black text-white">
              <AnimatedNum value={summary?.comfort_score} />
            </div>
            <div className="text-xs text-slate-500 mt-1">de 100 pontos</div>
          </div>
        </div>
      </div>
      
      {/* ── AI Forecast Chart ── */}
      <WeightForecastChart token={token} serverIP={serverIP} />
      
    </div>
    </div>
  );
}
