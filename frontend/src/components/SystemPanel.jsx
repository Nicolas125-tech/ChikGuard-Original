import React, { useState, useEffect, useCallback } from 'react';
import { getBaseUrl } from '../utils/config';
import { Activity, HardDrive, Cpu, Database, Server, Clock } from 'lucide-react';

export default function SystemPanel({ serverIP, prefs, token }) {
  const [health, setHealth] = useState(null);
  const baseUrl = getBaseUrl(serverIP);
  const pollMs = prefs?.statusMs || 5000;

  const loadHealth = useCallback(async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await fetch(`${baseUrl}/api/health/system`, { headers });
      if (res.ok) setHealth(await res.json());
    } catch (err) {
      console.error('Error fetching system health:', err);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    const bootstrap = setTimeout(loadHealth, 0);
    const timer = setInterval(loadHealth, pollMs);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
    };
  }, [loadHealth, pollMs]);

  const uptime = health ? `${Math.floor(health.uptime_seconds / 3600)}h ${Math.floor((health.uptime_seconds % 3600) / 60)}m` : '--';

  const MetricBar = ({ label, percent, icon: Icon, colorClass }) => (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Icon size={18} className="text-slate-400" />
          <span className="text-sm font-semibold tracking-wider text-slate-300">{label}</span>
        </div>
        <span className="text-xl font-bold">{percent !== undefined ? `${percent.toFixed(1)}%` : '--'}</span>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-3">
        <div className={`h-3 rounded-full transition-all duration-500 ease-out ${colorClass}`} style={{ width: `${percent || 0}%` }}></div>
      </div>
    </div>
  );

  const StatusCard = ({ label, value, icon: Icon, isOnline }) => (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-wider text-slate-400">{label}</span>
        <Icon size={16} className={isOnline ? "text-emerald-500" : "text-rose-500"} />
      </div>
      <div className="text-2xl font-bold flex items-center space-x-2">
        <div className={`w-3 h-3 rounded-full ${isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></div>
        <span>{value}</span>
      </div>
    </div>
  );

  return (
    <div className="space-y-6 animate-in fade-in zoom-in-95 duration-300">
      <div className="flex flex-col mb-6">
        <h2 className="text-2xl font-bold text-white">Saúde do Sistema e Telemetria</h2>
        <p className="text-slate-400 text-sm">Monitoramento em tempo real dos recursos do servidor de Edge e Cloud.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
        <MetricBar label="Uso de CPU" percent={health?.cpu} icon={Cpu} colorClass="bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)]" />
        <MetricBar label="Uso de Memória RAM" percent={health?.memory} icon={Activity} colorClass="bg-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.5)]" />
        <MetricBar label="Uso de Disco" percent={health?.disk} icon={HardDrive} colorClass="bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.5)]" />
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <StatusCard label="Servidor Principal" value={health ? "Online" : "Offline"} icon={Server} isOnline={!!health} />
        <StatusCard label="Banco de Dados" value={health?.database || 'Aguardando'} icon={Database} isOnline={health?.database === 'Online'} />
        <StatusCard label="Visão Computacional" value={health?.cv_pipeline || 'Aguardando'} icon={Activity} isOnline={health?.cv_pipeline === 'Online'} />
        <StatusCard label="Tempo em Atividade" value={uptime} icon={Clock} isOnline={true} />
      </div>
    </div>
  );
}
