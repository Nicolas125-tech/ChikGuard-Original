import React, { useState, useMemo, useEffect } from 'react';
import {
  LayoutDashboard, Bird, SlidersHorizontal, Activity, Database, Bell, History, Cpu, Settings, LogOut
} from 'lucide-react';
import OverviewPanel from '../components/OverviewPanel';
import BirdsPanel from '../components/BirdsPanel';
import DevicesPanel from '../components/DevicesPanel';
import SmartOpsPanel from '../components/SmartOpsPanel';
import ManagementPanel from '../components/ManagementPanel';
import AlertsPanel from '../components/AlertsPanel';
import HistoryPanel from '../components/HistoryPanel';
import SystemPanel from '../components/SystemPanel';
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
      { id: 'overview', label: 'Visao Geral', icon: LayoutDashboard },
      { id: 'birds', label: 'Aves Vistas', icon: Bird },
      { id: 'devices', label: 'Dispositivos', icon: SlidersHorizontal },
      { id: 'smart', label: 'IA + IoT', icon: Activity },
      { id: 'management', label: 'Gestao', icon: Database },
            { id: 'alerts', label: 'Alertas', icon: Bell },
      { id: 'history', label: 'Historico', icon: History },
      { id: 'system', label: 'Sistema', icon: Cpu },
      { id: 'settings', label: 'Configuracoes', icon: Settings },
      { id: 'admin', label: 'IAM Admin', icon: Database },

    ];
        if (role === 'viewer') {
      const allow = new Set(['overview', 'alerts', 'history', 'system']);
      return allTabs.filter(t => allow.has(t.id));
    }
    if (role === 'operator') {
      const allow = new Set(['overview', 'birds', 'devices', 'alerts', 'history', 'system']);
      return allTabs.filter(t => allow.has(t.id));
    }
    if (role !== 'superadmin' && role !== 'admin') {
      return allTabs.filter(t => t.id !== 'admin');
    }
    return allTabs;
  }, [role]);

  const canControlDevices = role === 'admin' || role === 'operator';


  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col font-sans">
      <header className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 sm:px-6 h-auto min-h-[5rem] py-3 sm:py-0 sm:h-20 flex flex-col sm:flex-row justify-between items-center sticky top-0 z-30 shadow-sm gap-4 sm:gap-0">
        <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-start">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500/10 p-1.5 rounded-xl border border-emerald-500/20 w-12 h-12 flex items-center justify-center shadow-inner">
              <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-9 h-9 object-contain drop-shadow-md" />
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-200">ChickGuard AI</h1>
          </div>
          <button onClick={onLogout} className="sm:hidden flex items-center gap-2 text-slate-400 hover:text-red-400 bg-slate-800/50 hover:bg-slate-800 px-3 py-1.5 rounded-lg transition-colors">
            <LogOut size={18} />
          </button>
        </div>

        <div className="flex items-center gap-1 sm:gap-2 w-full sm:w-auto overflow-x-auto pb-2 sm:pb-0 scrollbar-hide -mx-4 px-4 sm:mx-0 sm:px-0">
          {tabs.map((item) => {
            const Icon = item.icon;
            const isActive = tab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleTabChange(item.id)}
                className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl text-xs sm:text-sm font-semibold whitespace-nowrap flex flex-row items-center gap-2 transition-all duration-200 border shadow-sm ${
                  isActive
                    ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 ring-1 ring-emerald-500/20'
                    : 'bg-slate-800/40 border-slate-700/50 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <Icon size={16} className={isActive ? "text-emerald-400" : "text-slate-500"} />
                {item.label}
              </button>
            );
          })}
          <button onClick={onLogout} className="hidden sm:flex ml-4 items-center gap-2 text-slate-400 hover:text-red-400 font-medium px-4 py-2 rounded-xl hover:bg-red-500/10 transition-colors border border-transparent hover:border-red-500/20">
            <LogOut size={18} /><span>Sair</span>
          </button>
        </div>
      </header>

      <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto w-full animate-in fade-in duration-300">
        <div className="w-full">
          {tab === 'overview' && <OverviewPanel token={token} serverIP={serverIP} prefs={prefs} canControlDevices={canControlDevices} />}
          {tab === 'birds' && <BirdsPanel token={token} serverIP={serverIP} prefs={prefs} />}
          {tab === 'devices' && <DevicesPanel token={token} serverIP={serverIP} canControlDevices={canControlDevices} />}
          {tab === 'smart' && <SmartOpsPanel serverIP={serverIP} prefs={prefs} token={token} />}
          {tab === 'management' && <ManagementPanel serverIP={serverIP} prefs={prefs} />}
          {tab === 'alerts' && <AlertsPanel serverIP={serverIP} prefs={prefs} />}
          {tab === 'history' && <HistoryPanel serverIP={serverIP} prefs={prefs} />}
                {tab === 'system' && <SystemPanel serverIP={serverIP} />}
      {tab === 'settings' && <SettingsPanel serverIP={serverIP} token={token} prefs={prefs} onSavePrefs={onSavePrefs} onSaveServer={onSaveServer} />}
      {tab === 'admin' && <AdminPanel serverIP={serverIP} token={token} />}

        </div>
      </main>
    </div>
  );
}
