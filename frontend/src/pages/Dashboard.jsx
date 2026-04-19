import React, { useState, useMemo, useEffect } from 'react';
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
