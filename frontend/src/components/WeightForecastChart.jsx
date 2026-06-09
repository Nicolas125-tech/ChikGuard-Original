import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { TrendingUp, AlertCircle } from 'lucide-react';
import { getBaseUrl } from '@/utils/config';

export default function WeightForecastChart({ token, serverIP }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchForecast = async () => {
      try {
        const baseUrl = getBaseUrl(serverIP);
        const res = await fetch(`${baseUrl}/api/forecast/weight?target_weight=2800`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || 'Erro ao carregar previsão');
        }
        
        const forecastData = await res.json();
        setData(forecastData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchForecast();
  }, [token, serverIP]);

  if (loading) {
    return (
      <div className="card-premium p-6 flex flex-col items-center justify-center h-80 animate-pulse mt-6">
        <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-slate-400 font-medium tracking-wide">Modelando Regressão Polinomial (IA)...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-premium p-6 flex flex-col items-center justify-center h-80 border-rose-500/30 mt-6">
        <AlertCircle className="text-rose-400 mb-2" size={32} />
        <p className="text-slate-300 font-medium">{error}</p>
        <p className="text-slate-500 text-sm mt-2 text-center">A IA precisa de pelo menos 3 dias de histórico de peso para traçar a curva de crescimento.</p>
      </div>
    );
  }

  if (!data || !data.forecast || !data.forecast.projections) return null;

  const { target_date, target_weight, projections } = data.forecast;
  const currentDay = data.current_day;

  // Formatação para o gráfico
  const chartData = projections.map(p => ({
    dayLabel: `Dia ${p.day}`,
    day: p.day,
    peso: p.estimated_weight_g,
    date: p.date,
    isFuture: p.day > currentDay
  }));

  return (
    <div className="card-premium p-6 animate-fade-in-up mt-6 border-emerald-500/20">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
        <div>
          <div className="flex items-center gap-2 text-slate-400 font-semibold text-xs uppercase tracking-widest mb-1">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <TrendingUp size={16} className="text-emerald-400" />
            </div>
            Previsão de Abate via IA (Machine Learning)
          </div>
          <h3 className="text-xl font-bold text-white">Trajetória de Ganho de Peso</h3>
        </div>
        
        {target_date && (
          <div className="md:text-right bg-slate-900/50 p-3 rounded-xl border border-slate-800">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-widest">Peso Alvo Atingido Em</p>
            <p className="text-2xl font-black text-emerald-400">{new Date(target_date).toLocaleDateString('pt-BR')}</p>
          </div>
        )}
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 20, right: 30, bottom: 5, left: 0 }}>
            <defs>
              <linearGradient id="colorPeso" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis 
              dataKey="dayLabel" 
              stroke="#64748b" 
              fontSize={12} 
              tickLine={false}
              axisLine={false}
              minTickGap={20}
            />
            <YAxis 
              stroke="#64748b" 
              fontSize={12} 
              tickLine={false}
              axisLine={false}
              tickFormatter={(val) => `${val}g`}
              domain={['auto', 'auto']}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '12px', color: '#f8fafc', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }}
              itemStyle={{ color: '#10b981', fontWeight: 'bold' }}
              labelStyle={{ color: '#94a3b8', marginBottom: '4px', fontSize: '12px' }}
              formatter={(value, name, props) => {
                  const label = props.payload.isFuture ? 'Peso Projetado (IA)' : 'Peso Histórico';
                  return [`${value}g`, label];
              }}
              labelFormatter={(label, payload) => payload?.[0]?.payload?.date ? new Date(payload[0].payload.date).toLocaleDateString('pt-BR') : label}
            />
            <ReferenceLine y={target_weight} stroke="#f43f5e" strokeDasharray="4 4" label={{ position: 'insideTopLeft', value: `Alvo: ${target_weight}g`, fill: '#f43f5e', fontSize: 12, fontWeight: 'bold' }} />
            
            {currentDay && (
               <ReferenceLine x={`Dia ${currentDay}`} stroke="#3b82f6" strokeDasharray="3 3" label={{ position: 'insideTopRight', value: 'Hoje', fill: '#3b82f6', fontSize: 12 }} />
            )}

            <Line 
              type="monotone" 
              dataKey="peso" 
              stroke="#10b981" 
              strokeWidth={3} 
              dot={false} 
              activeDot={{ r: 6, fill: '#10b981', stroke: '#0f172a', strokeWidth: 3 }} 
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
