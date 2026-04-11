import React, { useState, useEffect, useCallback } from 'react';
import SystemCard from './SystemCard';
import { getBaseUrl } from '../utils/config';

export default function SystemPanel({ serverIP, prefs }) {
  const [info, setInfo] = useState(null);
  const [summary, setSummary] = useState(null);
  const baseUrl = getBaseUrl(serverIP);
  const pollMs = prefs?.statusMs || 5000;

  const loadSystem = useCallback(async () => {
    try {
      const [infoRes, summaryRes] = await Promise.all([
        fetch(`${baseUrl}/api/system-info`),
        fetch(`${baseUrl}/api/summary`),
      ]);
      if (infoRes.ok) setInfo(await infoRes.json());
      if (summaryRes.ok) setSummary(await summaryRes.json());
    } catch (e) {
      // Network error - keep previous state, do not crash
    }
  }, [baseUrl]);

  useEffect(() => {
    const bootstrap = setTimeout(loadSystem, 0);
    const timer = setInterval(loadSystem, pollMs);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
    };
  }, [loadSystem, pollMs]);

  const uptime = info ? `${Math.floor(info.uptime_seconds / 3600)}h ${Math.floor((info.uptime_seconds % 3600) / 60)}m` : '--';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-7xl mx-auto">
      <SystemCard label="Thread da Câmera" value={info?.camera_thread_alive ? 'Ativa' : 'Inativa'} />
      <SystemCard label="Processamento IA (YOLO)" value={info?.yolo_loaded ? 'Carregado' : 'Offline'} />
      <SystemCard label="Tempo em Atividade" value={uptime} />
      <SystemCard label="Média Térmica Global" value={summary ? `${summary.media_temperatura} °C` : '--'} />
      <SystemCard label="Total de Aves (Snapshots)" value={summary?.contagem_aves ?? '--'} />
      <SystemCard label="Alertas Críticos Ativos" value={summary?.total_alertas ?? '--'} />
    </div>
  );
}
