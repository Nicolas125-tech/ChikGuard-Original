import React, { useState, useEffect, useCallback } from 'react';
import { Cpu, Wind, Zap, SlidersHorizontal, Radio, Activity } from 'lucide-react';
import { getBaseUrl } from '../utils/config';

export default function IoTBridgePanel({ token, serverIP }) {
  const [iotStatus, setIotStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/api/iot/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIotStatus(data);
      }
    } catch (err) {
      console.error("Erro ao buscar status do IoT Bridge:", err);
    } finally {
      setLoading(false);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000); // Polling a cada 3s para o painel de debug
    return () => clearInterval(interval);
  }, [fetchStatus]);

  if (loading) return null;

  const isConnected = iotStatus?.mqtt_connected;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-sm mt-6 mb-6">
      <div className="flex items-center gap-3 mb-6">
        <div className={`p-2.5 rounded-xl border ${isConnected ? 'bg-emerald-500/20 border-emerald-500/30' : 'bg-rose-500/20 border-rose-500/30'}`}>
          <Radio size={24} className={isConnected ? "text-emerald-400" : "text-rose-400"} />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Ponte IoT MQTT (Sensores Locais)</h2>
          <p className="text-xs text-slate-400 mt-1">Conexão direta com ESP32/Arduinos via Mosquitto</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-950/50 p-4 rounded-2xl border border-slate-800/80">
          <div className="text-slate-400 text-xs font-semibold mb-1">Status do Broker</div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></div>
            <span className="text-white font-bold">{isConnected ? 'CONECTADO' : 'DESCONECTADO'}</span>
          </div>
          <div className="text-slate-500 text-xs mt-1 truncate">{iotStatus?.broker || 'N/A'}</div>
        </div>

        <div className="bg-slate-950/50 p-4 rounded-2xl border border-slate-800/80">
           <div className="text-slate-400 text-xs font-semibold mb-1">Tópico Assinado</div>
           <div className="text-white font-mono text-sm break-all">{iotStatus?.topic || 'N/A'}</div>
           <div className="text-slate-500 text-xs mt-1">
             Fonte Atual: <span className="text-indigo-300 font-medium">{iotStatus?.current_sensor_source}</span>
           </div>
        </div>

        <div className="bg-slate-950/50 p-4 rounded-2xl border border-slate-800/80 flex flex-col justify-center">
           <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-xs font-semibold">Mensagens Recebidas</span>
              <Activity size={14} className="text-indigo-400" />
           </div>
           <div className="text-2xl font-bold text-white mb-1">
             {iotStatus?.messages_received || 0}
           </div>
           <div className="text-slate-500 text-xs">
             Última leitura: {iotStatus?.last_message_at ? new Date(iotStatus.last_message_at * 1000).toLocaleTimeString('pt-BR') : 'Nunca'}
           </div>
        </div>
      </div>
    </div>
  );
}
