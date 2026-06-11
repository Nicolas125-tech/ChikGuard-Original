import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { Skull, AlertTriangle, Activity } from 'lucide-react';
import { getBaseUrl } from '../utils/config';

export default function MortalityForecastChart({ token, serverIP }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMortality = async () => {
      try {
        const res = await fetch(`${getBaseUrl(serverIP)}/api/forecast/mortality`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Erro ao carregar previsão de mortalidade');
        
        const json = await res.json();
        setData(json);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchMortality();
  }, [token, serverIP]);

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col items-center justify-center h-80 animate-pulse mt-6">
        <Activity className="text-rose-500 animate-pulse mb-4" size={32} />
        <p className="text-slate-400 font-medium">Analisando Riscos de Mortalidade (IA)...</p>
      </div>
    );
  }

  if (error || !data) {
    return null;
  }

  const { projections, current_day, avg_recent_temp } = data;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0].payload;
      return (
        <div className="bg-slate-900 border border-slate-700 p-3 rounded-xl shadow-xl">
          <p className="text-white font-bold mb-1">{dataPoint.is_forecast ? 'Previsão: ' : 'Histórico: '} {dataPoint.date}</p>
          <p className="text-slate-300 text-sm">Dia do Lote: {dataPoint.day}</p>
          <p className="text-rose-400 font-medium text-sm mt-2">
            Risco Estimado: {dataPoint.risk_pct.toFixed(2)}%
          </p>
          {dataPoint.stress_factor > 1.2 && (
            <p className="text-amber-400 text-xs mt-1 flex items-center gap-1">
              <AlertTriangle size={12} /> Fator de Estresse Elevado
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-slate-900 border border-rose-900/30 rounded-3xl p-6 mt-6 shadow-sm">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
          <div className="flex items-center gap-2 text-slate-400 font-semibold text-xs uppercase tracking-widest mb-1">
            <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
              <Skull size={16} className="text-rose-400" />
            </div>
            Previsão de Risco de Mortalidade
          </div>
          <h3 className="text-xl font-bold text-white">Projeção Baseada em Estresse Térmico</h3>
        </div>
        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Temperatura Média Recente</p>
          <p className="text-2xl font-black text-rose-400">{avg_recent_temp}°C</p>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={projections} margin={{ top: 20, right: 10, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis 
              dataKey="day" 
              stroke="#64748b" 
              tick={{fill: '#94a3b8', fontSize: 12}} 
              tickFormatter={(v) => `Dia ${v}`} 
            />
            <YAxis 
              stroke="#64748b" 
              tick={{fill: '#94a3b8', fontSize: 12}}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{fill: '#1e293b', opacity: 0.4}} />
            <ReferenceLine x={current_day} stroke="#3b82f6" strokeDasharray="3 3" label={{ value: 'HOJE', position: 'insideTopLeft', fill: '#60a5fa', fontSize: 10 }} />
            <Bar dataKey="risk_pct" radius={[4, 4, 0, 0]}>
              {projections.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.is_forecast ? (entry.stress_factor > 1.2 ? '#f43f5e' : '#fb923c') : '#475569'} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 flex flex-wrap gap-4 text-xs font-medium text-slate-400 justify-center">
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-slate-600"></div> Histórico</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-orange-400"></div> Risco Moderado</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-rose-500"></div> Risco Elevado</div>
      </div>
    </div>
  );
}
