import os

components_dir = 'c:/nic/ChikGuard-Original/frontend/src/components'
pages_dir = 'c:/nic/ChikGuard-Original/frontend/src/pages'

camera_panel_code = '''import React, { useState } from 'react';
import { Maximize, WifiOff } from 'lucide-react';
import WebRTCVideo from './WebRTCVideo';
import HeatmapOverlay from './HeatmapOverlay';
import { getBaseUrl } from '../utils/config';

export default function CameraPanel({ token, serverIP }) {
  const [videoBlocked, setVideoBlocked] = useState(false);
  const [showHeatmapOverlay, setShowHeatmapOverlay] = useState(false);
  
  const baseUrl = getBaseUrl(serverIP);
  const webrtcUrl = `${baseUrl}/api/webrtc/offer`;

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col gap-4">
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-3xl overflow-hidden h-full relative flex flex-col shadow-sm backdrop-blur-sm">
        <div className="p-4 border-b border-slate-800/80 flex flex-row justify-between items-center bg-slate-950/80 backdrop-blur-md absolute top-0 left-0 right-0 z-20">
          <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm uppercase tracking-wider">
            <Maximize size={16} className="text-emerald-400" /> Câmera Principal
          </h3>
          <button 
            onClick={() => setShowHeatmapOverlay(v => !v)}
            className="text-xs font-semibold bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 rounded-lg px-3 py-1.5 transition-colors"
          >
            {showHeatmapOverlay ? 'Ocultar Heatmap' : 'Mostrar Heatmap AI'}
          </button>
        </div>

        <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden h-full">
          {videoBlocked ? (
            <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-950/50 absolute inset-0">
              <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 flex flex-col items-center">
                <WifiOff size={40} className="text-slate-600 mb-4" />
                <p className="text-slate-400 font-medium">Aguardando Conexão com Câmera Real</p>
                <p className="text-slate-500 text-xs mt-2">Sem simuladores disponíveis</p>
              </div>
            </div>
          ) : (
            <>
              <WebRTCVideo 
                url={webrtcUrl} 
                token={token} 
                className="absolute inset-0 w-full h-full object-contain z-0" 
                onConnectionStateChange={(state) => { 
                  if(state === 'failed' || state === 'disconnected' || state === 'closed') { 
                    setVideoBlocked(true); 
                  } 
                }} 
              />
              {showHeatmapOverlay && <HeatmapOverlay serverIP={serverIP} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
'''

climate_panel_code = '''import React, { useState, useEffect, useCallback } from 'react';
import { Wind, Zap, Thermometer, LayoutDashboard } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getBaseUrl } from '../utils/config';

export default function ClimatePanel({ token, serverIP, prefs, canControlDevices }) {
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [historico, setHistorico] = useState([]);
  const [erro, setErro] = useState(false);
  const baseUrl = getBaseUrl(serverIP);

  const fetchDevices = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Device state fetch failed');
      const data = await r.json();
      setDispositivos(data || { ventilacao: false, aquecedor: false });
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/history`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('History fetch failed');
      const data = await r.json();
      setHistorico(data || []);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    fetchDevices();
    fetchHistory();
    const c = setInterval(fetchDevices, prefs.devicesMs);
    const h = setInterval(fetchHistory, prefs.historyMs);
    return () => { clearInterval(c); clearInterval(h); };
  }, [fetchDevices, fetchHistory, prefs]);

  const toggleDevice = async (tipo, ligar) => {
    if (!canControlDevices) return;
    try {
        await fetch(`${baseUrl}/api/${tipo}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ligar }),
        });
        fetchDevices();
    } catch (e) {
        console.error(e);
    }
  };

  return (
    <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
      <div className="space-y-6">
        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
            <h3 className="text-slate-400 text-sm font-semibold uppercase mb-4 flex items-center gap-2 tracking-widest">
                <Thermometer size={18} className="text-rose-400" /> Controle de Dispositivos (IoT)
            </h3>
            <div className="grid grid-cols-2 gap-4 h-48">
              <button 
                disabled={!canControlDevices} 
                onClick={() => toggleDevice('ventilacao', !dispositivos.ventilacao)} 
                className={`border p-5 rounded-2xl flex flex-col items-center justify-center gap-3 transition-all ${dispositivos.ventilacao ? 'border-blue-500/50 bg-blue-500/10 shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-slate-800 bg-slate-950 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed hidden-disabled' : 'hover:-translate-y-1'}`}
              >
                <Wind size={40} className={dispositivos.ventilacao ? "text-blue-400" : "text-slate-500"} />
                <span className={`text-sm font-bold tracking-wide uppercase ${dispositivos.ventilacao ? "text-blue-300" : "text-slate-400"}`}>Ventilar</span>
              </button>
              
              <button 
                disabled={!canControlDevices} 
                onClick={() => toggleDevice('aquecedor', !dispositivos.aquecedor)} 
                className={`border p-5 rounded-2xl flex flex-col items-center justify-center gap-3 transition-all ${dispositivos.aquecedor ? 'border-orange-500/50 bg-orange-500/10 shadow-[0_0_15px_rgba(249,115,22,0.15)]' : 'border-slate-800 bg-slate-950 hover:border-slate-700'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed hidden-disabled' : 'hover:-translate-y-1'}`}
              >
                <Zap size={40} className={dispositivos.aquecedor ? "text-orange-400" : "text-slate-500"} />
                <span className={`text-sm font-bold tracking-wide uppercase ${dispositivos.aquecedor ? "text-orange-300" : "text-slate-400"}`}>Aquecer</span>
              </button>
            </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm h-full">
          <h3 className="text-slate-400 text-sm font-semibold uppercase mb-4 flex items-center gap-2 tracking-widest">
            <LayoutDashboard size={16} className="text-amber-400" /> Histórico Térmico
          </h3>
          <div className="h-64 w-full -ml-2">
            {historico.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historico} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="hora" stroke="#64748b" fontSize={10} tickMargin={8} />
                  <YAxis domain={['dataMin - 2', 'dataMax + 2']} stroke="#64748b" fontSize={10} tickMargin={8} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px' }} itemStyle={{ color: '#10b981', fontWeight: 'bold' }} />
                  <Line type="monotone" dataKey="temp" stroke="#10b981" strokeWidth={3} dot={{ fill: '#0f172a', stroke: '#10b981', strokeWidth: 2, r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-slate-500 text-sm font-medium bg-slate-950/30 rounded-xl">Sem dados térmicos reportados.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
'''

overview_panel_code = '''import React, { useState, useEffect, useCallback } from 'react';
import { Thermometer, Bird, CheckCircle, Activity } from 'lucide-react';
import { getBaseUrl } from '../utils/config';

export default function OverviewPanel({ token, serverIP, prefs }) {
  const [dados, setDados] = useState(null);
  const [contagem, setContagem] = useState(null);
  const [summary, setSummary] = useState(null);
  const baseUrl = getBaseUrl(serverIP);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/status`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) setDados(await r.json());
    } catch (e) {}
  }, [baseUrl, token]);

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

  return (
    <div className="grid gap-6 grid-cols-1 md:grid-cols-3">
        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400 font-semibold text-sm uppercase tracking-widest mb-4">
            <Thermometer size={18} className="text-rose-400" /> Temperatura Média
          </div>
          <div className="text-6xl font-black text-white mb-3 tracking-tighter drop-shadow-sm">
            {dados?.temperatura ?? '--'} <span className="text-4xl text-slate-500 font-bold tracking-normal">°C</span>
          </div>
          <div className="inline-flex px-4 py-1.5 rounded-lg font-bold text-sm bg-slate-950/60 border border-white/5 shadow-inner text-slate-300">
            {dados?.status || 'Aguardando Conexão'}
          </div>
        </div>

        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2 text-slate-400 font-semibold text-sm uppercase tracking-widest">
              <Bird size={18} className="text-indigo-400" /> Detecções
            </div>
            <CheckCircle className="text-emerald-500 drop-shadow-sm" size={20} />
          </div>
          <div className="text-6xl font-black text-white tracking-tighter drop-shadow-sm">
            {contagem ?? '--'} <span className="text-xl text-slate-500 font-bold tracking-normal uppercase ml-1">aves</span>
          </div>
        </div>

        <div className="p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
          <div className="text-sm uppercase font-semibold tracking-widest text-slate-400 mb-2 flex items-center gap-2">
            <Activity size={18} className="text-emerald-400"/> Score de Conforto
          </div>
          <div className="text-5xl font-black text-white drop-shadow-sm mt-4">
            {summary?.comfort_score ?? '--'}
          </div>
          <div className="w-full h-4 bg-slate-950 rounded-full mt-6 overflow-hidden border border-slate-800/50 shadow-inner">
            <div 
              className={`h-full transition-all duration-1000 ease-out ${Number(summary?.comfort_score || 0) >= 80 ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' : Number(summary?.comfort_score || 0) >= 60 ? 'bg-gradient-to-r from-yellow-500 to-amber-400' : 'bg-gradient-to-r from-red-600 to-rose-500'}`}
              style={{ width: `${Math.max(0, Math.min(100, Number(summary?.comfort_score || 0)))}%` }}
            />
          </div>
        </div>
    </div>
  );
}
'''

dashboard_panel_code = '''import React, { useState, useMemo, useEffect } from 'react';
import { LayoutDashboard, Camera, Wind, History, Settings, Database, LogOut } from 'lucide-react';

import OverviewPanel from '../components/OverviewPanel';
import CameraPanel from '../components/CameraPanel';
import ClimatePanel from '../components/ClimatePanel';
import HistoryPanel from '../components/HistoryPanel';
import SettingsPanel from '../components/SettingsPanel';
import AdminPanel from '../components/AdminPanel';

export default function Dashboard({ token, role, serverIP, prefs, onSavePrefs, onSaveServer, onLogout }) {
  const [tab, setTab] = useState(() => {
    const hash = window.location.hash.replace('#', '');
    return hash || 'overview';
  });

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      setTab(hash || 'overview');
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleTabChange = (newTab) => {
    if (window.location.hash !== `#${newTab}`) {
      window.location.hash = newTab;
    }
  };

  const tabs = useMemo(() => {
    const allTabs = [
      { id: 'overview', label: 'Visão Geral', icon: LayoutDashboard },
      { id: 'camera', label: 'Câmeras Ao Vivo', icon: Camera },
      { id: 'climate', label: 'Clima & IoT', icon: Wind },
      { id: 'history', label: 'Histórico & Relatórios', icon: History },
      { id: 'settings', label: 'Configurações', icon: Settings },
      { id: 'admin', label: 'Gerenciar Acessos', icon: Database },
    ];
    
    // RBAC Control for visible tabs
    if (role === 'viewer') {
      const allow = new Set(['overview', 'camera', 'history']);
      return allTabs.filter(t => allow.has(t.id));
    }
    if (role === 'operator') {
      const allow = new Set(['overview', 'camera', 'climate', 'history']);
      return allTabs.filter(t => allow.has(t.id));
    }
    if (role !== 'superadmin' && role !== 'admin') {
      return allTabs.filter(t => t.id !== 'admin' && t.id !== 'settings');
    }
    return allTabs;
  }, [role]);

  const canControlDevices = role === 'admin' || role === 'operator' || role === 'superadmin';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 flex font-sans overflow-hidden">
      {/* Sidebar Corporativa */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col z-40 relative hidden md:flex shrink-0">
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="bg-emerald-500/10 p-1.5 rounded-xl border border-emerald-500/20 w-10 h-10 flex items-center justify-center shadow-inner">
            <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-7 h-7 object-contain drop-shadow-md" />
          </div>
          <h1 className="text-xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200">
            ChickGuard
          </h1>
        </div>

        <div className="flex-1 overflow-y-auto py-6 px-4 space-y-2">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest px-3 mb-2">Monitoramento</div>
            {tabs.map((item) => {
              const Icon = item.icon;
              const isActive = tab === item.id;
              
              // Separator logic
              if (item.id === 'settings') {
                  return (
                      <React.Fragment key="sep1">
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest px-3 mt-6 mb-2">Administração</div>
                        <button
                            onClick={() => handleTabChange(item.id)}
                            className={`w-full text-left px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-3 transition-colors ${isActive ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent'}`}
                        >
                            <Icon size={18} className={isActive ? "text-emerald-400" : "text-slate-500"} />
                            {item.label}
                        </button>
                      </React.Fragment>
                  );
              }
              
              if (item.id === 'admin') {
                  return (
                    <button key={item.id}
                        onClick={() => handleTabChange(item.id)}
                        className={`w-full text-left px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-3 transition-colors ${isActive ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent'}`}
                    >
                        <Icon size={18} className={isActive ? "text-emerald-400" : "text-slate-500"} />
                        {item.label}
                    </button>
                  );
              }

              return (
                <button
                  key={item.id}
                  onClick={() => handleTabChange(item.id)}
                  className={`w-full text-left px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-3 transition-colors ${isActive ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent'}`}
                >
                  <Icon size={18} className={isActive ? "text-emerald-400" : "text-slate-500"} />
                  {item.label}
                </button>
              );
            })}
        </div>

        <div className="p-4 border-t border-slate-800">
            <div className="flex items-center gap-3 mb-4 px-2">
                <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-300 uppercase">
                    {role[0]}
                </div>
                <div className="flex flex-col">
                    <span className="text-xs font-semibold text-slate-200 uppercase">{role}</span>
                    <span className="text-[10px] text-slate-500">Logado no sistema</span>
                </div>
            </div>
            <button onClick={onLogout} className="w-full bg-red-500/10 hover:bg-red-500/20 text-red-400 font-medium px-4 py-2.5 rounded-xl transition-colors border border-transparent hover:border-red-500/20 flex justify-center items-center gap-2">
                <LogOut size={16} /><span>Desconectar</span>
            </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen relative overflow-y-auto">
        {/* Mobile Header */}
        <header className="md:hidden bg-slate-900 border-b border-slate-800 px-4 py-3 flex justify-between items-center z-30 sticky top-0">
           <h1 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200">ChickGuard</h1>
           <button onClick={onLogout} className="p-2 border border-slate-800 rounded-lg text-slate-400"><LogOut size={18} /></button>
        </header>

        <div className="p-4 sm:p-6 lg:p-10 max-w-7xl mx-auto w-full animate-in fade-in duration-300">
            <div className="mb-8">
                <h2 className="text-2xl font-bold text-white capitalize">{tabs.find(t => t.id === tab)?.label}</h2>
                <p className="text-slate-500 text-sm mt-1">Gerencie a produção em tempo real.</p>
            </div>

            <div className="w-full">
            {tab === 'overview' && <OverviewPanel token={token} serverIP={serverIP} prefs={prefs} />}
            {tab === 'camera' && <CameraPanel token={token} serverIP={serverIP} />}
            {tab === 'climate' && <ClimatePanel token={token} serverIP={serverIP} prefs={prefs} canControlDevices={canControlDevices} />}
            {tab === 'history' && <HistoryPanel serverIP={serverIP} prefs={prefs} />}
            {tab === 'settings' && <SettingsPanel serverIP={serverIP} token={token} prefs={prefs} onSavePrefs={onSavePrefs} onSaveServer={onSaveServer} />}
            {tab === 'admin' && <AdminPanel serverIP={serverIP} token={token} />}
            </div>
        </div>
      </main>
    </div>
  );
}
'''

def write_and_log(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Written: {path}")

write_and_log(f"{components_dir}/CameraPanel.jsx", camera_panel_code)
write_and_log(f"{components_dir}/ClimatePanel.jsx", climate_panel_code)
write_and_log(f"{components_dir}/OverviewPanel.jsx", overview_panel_code)
write_and_log(f"{pages_dir}/Dashboard.jsx", dashboard_panel_code)
