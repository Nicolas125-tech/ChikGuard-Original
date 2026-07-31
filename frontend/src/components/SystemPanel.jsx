import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Database, Server, Clock, Cpu, HardDrive } from 'lucide-react';
import { isDeepEqual } from '../utils/performance';

const MetricBar = React.memo(({ label, percent, icon, colorClass }) => (
  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-slate-800 rounded-lg">
          {icon && React.createElement(icon, { size: 18, className: "text-slate-400" })}
        </div>
        <span className="text-slate-400 font-medium text-sm">{label}</span>
      </div>
      <span className="text-white font-bold text-lg">{percent !== undefined ? `${percent}%` : '--'}</span>
    </div>
    <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
      <div className={`h-2.5 rounded-full ${colorClass}`} style={{ width: `${percent || 0}%` }}></div>
    </div>
  </div>
));

const StatusCard = React.memo(({ label, value, icon, isOnline }) => (
  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
    <div className="flex items-center justify-between mb-3">
      <div className="p-2 bg-slate-800 rounded-lg">
        {icon && React.createElement(icon, { size: 18, className: isOnline ? "text-emerald-400" : "text-slate-400" })}
      </div>
      <div className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
    </div>
    <div className="text-slate-400 text-sm font-medium mb-1">{label}</div>
    <div className="text-white font-bold text-lg truncate">{value}</div>
  </div>
));

export default function SystemPanel({ serverIP, prefs, token }) {
  const [health, setHealth] = useState(null);
  const baseUrl = serverIP ? `http://${serverIP}` : '';
  const pollMs = prefs?.statusMs || 5000;

  const loadHealth = useCallback(async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await fetch(`${baseUrl}/api/health/system`, { headers });
      // Bolt Optimization: Prevent unnecessary re-renders when polling data is identical.
      if (res.ok) {
        const data = await res.json();
        setHealth(prev => isDeepEqual(prev, data) ? prev : data);
      }
    } catch (err) {
      console.error('Error fetching system health:', err);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    (async () => { loadHealth(); })();
    const timer = setInterval(loadHealth, pollMs);
    return () => {
      clearInterval(timer);
    };
  }, [loadHealth, pollMs]);

  const uptime = health ? `${Math.floor(health.uptime_seconds / 3600)}h ${Math.floor((health.uptime_seconds % 3600) / 60)}m` : '--';

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
