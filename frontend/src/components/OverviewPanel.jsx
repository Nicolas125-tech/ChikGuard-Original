import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Thermometer, Bird, Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { getBaseUrl } from '../utils/config';

/* ── Animated Number ─────────────────────────────────────────── */
function AnimatedNum({ value, decimals = 0 }) {
  const [display, setDisplay] = useState(value);
  const prev = useRef(value);

  useEffect(() => {
    if (value === null || value === undefined) return;
    const from = prev.current ?? 0;
    const to = Number(value);
    prev.current = to;
    if (isNaN(to)) { setDisplay(value); return; }

    const duration = 600;
    const start = performance.now();
    const animate = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = from + (to - from) * eased;
      setDisplay(decimals > 0 ? current.toFixed(decimals) : Math.round(current));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [value, decimals]);

  return <>{display ?? '--'}</>;
}

/* ── Score Ring (SVG mini gauge) ──────────────────────────────── */
function ScoreRing({ score, size = 100 }) {
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
}

export default function OverviewPanel({ token, serverIP, prefs }) {
  const [dados, setDados] = useState(null);
  const [contagem, setContagem] = useState(null);
  const [summary, setSummary] = useState(null);
  const [prevTemp, setPrevTemp] = useState(null);
  const baseUrl = getBaseUrl(serverIP);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/status`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) {
        const d = await r.json();
        setPrevTemp(dados?.temperatura ?? null);
        setDados(d);
      }
    } catch (e) {}
  }, [baseUrl, token, dados]);

  const fetchCount = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/chick_count`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) {
        const d = await r.json();
        setContagem(d.count);
      }
    } catch (e) {}
  }, [baseUrl, token]);

  const fetchSummary = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/summary`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) setSummary(await r.json());
    } catch (e) {}
  }, [baseUrl, token]);

  useEffect(() => {
    fetchStatus(); fetchCount(); fetchSummary();
    const a = setInterval(fetchStatus, prefs.statusMs);
    const b = setInterval(fetchCount, prefs.countMs);
    const c = setInterval(fetchSummary, prefs.statusMs);
    return () => { clearInterval(a); clearInterval(b); clearInterval(c); };
  }, [fetchStatus, fetchCount, fetchSummary, prefs]);

  const temp = dados?.temperatura;
  const tempTrend = prevTemp !== null && temp !== null
    ? (temp > prevTemp ? 'up' : temp < prevTemp ? 'down' : 'stable')
    : null;

  return (
    <div className="grid gap-5 grid-cols-1 md:grid-cols-3">
      {/* ── Temperatura ── */}
      <div className="card-premium p-6 animate-fade-in-up stagger-1 hover-lift">
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
      <div className="card-premium p-6 animate-fade-in-up stagger-2 hover-lift">
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
      <div className="card-premium p-6 animate-fade-in-up stagger-3 hover-lift">
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
    </div>
  );
}
