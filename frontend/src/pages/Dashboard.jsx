import React, { useState, useMemo, useEffect, useCallback } from 'react';
import ChickenPhoto from '../components/ChickenPhoto';

import {
  LayoutDashboard, Camera, Layers, Wind, History, Settings, Database,
  LogOut, Bird, Bell, Cpu, BarChart3, Shield, Menu, X,
  Wifi, WifiOff, ChevronRight
} from 'lucide-react';

import OverviewPanel from '../components/OverviewPanel';
import CameraPanel from '../components/CameraPanel';
import ClimatePanel from '../components/ClimatePanel';
import HistoryPanel from '../components/HistoryPanel';
import SettingsPanel from '../components/SettingsPanel';
import AdminPanel from '../components/AdminPanel';
import BirdsPanel from '../components/BirdsPanel';
import AlertsPanel from '../components/AlertsPanel';
import SmartOpsPanel from '../components/SmartOpsPanel';
import ManagementPanel from '../components/ManagementPanel';
import DevicesPanel from '../components/DevicesPanel';
import SystemPanel from '../components/SystemPanel';
import DigitalTwinPanel from '../components/DigitalTwinPanel';
import { getBaseUrl } from '../utils/config';

export default function Dashboard({ token, role, serverIP, prefs, onSavePrefs, onSaveServer, onLogout }) {
  const [tab, setTab] = useState(() => {
    const hash = window.location.hash.replace('#', '');
    return hash || 'overview';
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState(null);
  const [alertCount, setAlertCount] = useState(0);
  const [clock, setClock] = useState('');

  const baseUrl = getBaseUrl(serverIP);
  const canControlDevices = role === 'admin' || role === 'operator' || role === 'superadmin';

  // ── Sincronização de Rotas por Hash ──
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
    setMobileMenuOpen(false);
  };

  // ── Relógio de Tempo Real ──
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setClock(now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }));
    };
    updateClock();
    const clockTimer = setInterval(updateClock, 30000);
    return () => clearInterval(clockTimer);
  }, []);

  // ── Monitor de Status do Servidor ──
  const checkHealth = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);
      const response = await fetch(`${baseUrl}/api/status`, {
        signal: controller.signal,
        headers: { Authorization: `Bearer ${token}` }
      });
      clearTimeout(timeoutId);
      setBackendOnline(response.ok);
    } catch {
      setBackendOnline(false);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    checkHealth();
    const healthTimer = setInterval(checkHealth, 15000);
    return () => clearInterval(healthTimer);
  }, [checkHealth]);

  // ── Monitor de Contagem de Alertas ──
  const fetchAlertCount = useCallback(async () => {
    try {
      const response = await fetch(`${baseUrl}/api/alerts`);
      if (response.ok) {
        const data = await response.json();
        setAlertCount(Array.isArray(data) ? data.length : 0);
      }
    } catch {}
  }, [baseUrl]);

  useEffect(() => {
    fetchAlertCount();
    const alertsTimer = setInterval(fetchAlertCount, 20000);
    return () => clearInterval(alertsTimer);
  }, [fetchAlertCount]);

  // ── Definições de Permissões das Abas (RBAC) ──
  const tabs = useMemo(() => {
    const sections = [
      {
        title: 'Monitoramento',
        items: [
          { id: 'overview',  label: 'Visão Geral',        icon: LayoutDashboard },
          { id: 'camera',    label: 'Câmeras Ao Vivo',    icon: Camera },
          { id: 'digitaltwin', label: 'Gêmeo Digital 2D', icon: Layers },
          { id: 'birds',     label: 'Aves & Tracking',    icon: ChickenPhoto },
          { id: 'alerts',    label: 'Alertas',            icon: Bell, badge: alertCount },
        ]
      },
      {
        title: 'Operações',
        items: [
          { id: 'climate',   label: 'Clima & IoT',        icon: Wind },
          { id: 'smartops',  label: 'Operações Smart',    icon: Cpu },
          { id: 'management',label: 'Gestão Avançada',    icon: BarChart3 },
          { id: 'devices',   label: 'Dispositivos',       icon: Shield },
          { id: 'history',   label: 'Histórico',          icon: History },
        ]
      },
      {
        title: 'Administração',
        items: [
          { id: 'settings',  label: 'Configurações',      icon: Settings },
          { id: 'admin',     label: 'Gerenciar Acessos',  icon: Database },
        ]
      },
    ];

    if (role === 'viewer') {
      const allow = new Set(['overview', 'camera', 'digitaltwin', 'birds', 'alerts', 'history']);
      return sections.map(s => ({ ...s, items: s.items.filter(t => allow.has(t.id)) })).filter(s => s.items.length > 0);
    }
    if (role === 'operator') {
      const allow = new Set(['overview', 'camera', 'digitaltwin', 'birds', 'alerts', 'climate', 'smartops', 'devices', 'history']);
      return sections.map(s => ({ ...s, items: s.items.filter(t => allow.has(t.id)) })).filter(s => s.items.length > 0);
    }
    if (role !== 'superadmin' && role !== 'admin') {
      return sections.map(s => ({ ...s, items: s.items.filter(t => t.id !== 'admin' && t.id !== 'settings') })).filter(s => s.items.length > 0);
    }
    return sections;
  }, [role, alertCount]);

  const allItems = tabs.flatMap(s => s.items);
  const currentTab = allItems.find(t => t.id === tab);

  // ── Sub-componente de Renderização do Conteúdo da Sidebar ──
  const SidebarContent = () => (
    <>
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {tabs.map((section, si) => (
          <div key={si} className={si > 0 ? 'mt-6' : ''}>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.15em] px-3 mb-2">
              {section.title}
            </div>
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = tab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleTabChange(item.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium flex items-center gap-3 transition-all duration-200 group relative ${
                    isActive
                      ? 'bg-emerald-500/12 text-emerald-400 shadow-sm shadow-emerald-500/5'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                  }`}
                >
                  <Icon
                    size={17}
                    className={`transition-colors ${isActive ? 'text-emerald-400' : 'text-slate-500 group-hover:text-slate-400'}`}
                  />
                  <span className="flex-1">{item.label}</span>
                  {item.badge > 0 && (
                    <span className="bg-rose-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center leading-tight animate-pulse-glow shadow-md shadow-rose-500/20">
                      {item.badge}
                    </span>
                  )}
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-emerald-400 rounded-r-full" />
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-slate-800/60">
        <div className="flex items-center gap-3 mb-3 px-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-xs font-bold text-white uppercase shadow-md">
            {role[0]}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-semibold text-slate-200 uppercase truncate">{role}</span>
            <span className="text-[10px] text-slate-500 truncate">
              {localStorage.getItem('cg_username') || 'Sistema'}
            </span>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="w-full bg-red-500/8 hover:bg-red-500/15 text-red-400 font-medium px-3 py-2.5 rounded-xl transition-all border border-transparent hover:border-red-500/20 flex justify-center items-center gap-2 text-sm"
        >
          <LogOut size={15} /><span>Desconectar</span>
        </button>
      </div>
    </>
  );

  // ── Métodos de Renderização Secundários (Clean Code Layout) ──

  const renderDesktopSidebar = () => (
    <aside className="w-60 bg-slate-900/80 border-r border-slate-800/60 flex-col z-40 relative hidden md:flex shrink-0 glass">
      <div className="p-5 border-b border-slate-800/60 flex items-center gap-3">
        <div className="bg-emerald-500/10 p-1.5 rounded-xl border border-emerald-500/20 w-9 h-9 flex items-center justify-center shadow-inner">
          <img src="/logo.jpeg" alt="ChikGuard" className="w-6 h-6 object-contain drop-shadow-md" />
        </div>
        <h1 className="text-lg font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200">
          ChickGuard
        </h1>
      </div>
      <SidebarContent />
    </aside>
  );

  const renderMobileSidebar = () => {
    if (!mobileMenuOpen) return null;
    return (
      <div className="fixed inset-0 z-50 md:hidden">
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
        <aside className="absolute left-0 top-0 bottom-0 w-72 bg-slate-900 border-r border-slate-800 flex flex-col animate-slide-in-left shadow-2xl">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-emerald-500/10 p-1.5 rounded-xl border border-emerald-500/20 w-9 h-9 flex items-center justify-center">
                <img src="/logo.jpeg" alt="ChikGuard" className="w-6 h-6 object-contain" />
              </div>
              <span className="text-lg font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200">ChickGuard</span>
            </div>
            <button aria-label="Close mobile menu" onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors">
              <X size={20} />
            </button>
          </div>
          <SidebarContent />
        </aside>
      </div>
    );
  };

  const renderHeader = () => (
    <header className="bg-slate-900/60 border-b border-slate-800/50 px-4 md:px-6 py-3 flex justify-between items-center z-30 sticky top-0 glass shrink-0">
      <div className="flex items-center gap-3">
        <button
          aria-label="Open mobile menu"
          onClick={() => setMobileMenuOpen(true)}
          className="md:hidden p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors border border-slate-800"
        >
          <Menu size={20} />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-sm">
          <span className="text-slate-500 font-medium">Dashboard</span>
          <ChevronRight size={14} className="text-slate-600" />
          <span className="text-white font-semibold">{currentTab?.label || 'Visão Geral'}</span>
        </div>
        <h1 className="sm:hidden text-base font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200">ChickGuard</h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 bg-slate-800/60 px-3 py-1.5 rounded-lg border border-slate-700/50 text-xs">
          <div className={`status-dot ${backendOnline ? 'online' : backendOnline === false ? 'offline' : ''}`} />
          <span className={`font-medium ${backendOnline ? 'text-emerald-400' : backendOnline === false ? 'text-red-400' : 'text-slate-500'}`}>
            {backendOnline ? 'Online' : backendOnline === false ? 'Offline' : 'Verificando...'}
          </span>
        </div>

        <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 font-mono bg-slate-800/40 px-3 py-1.5 rounded-lg border border-slate-800/50">
          {clock}
        </div>

        <button
          aria-label="View alerts"
          onClick={() => handleTabChange('alerts')}
          className="relative p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors border border-slate-800/50 hover:border-slate-700"
        >
          <Bell size={18} />
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[9px] font-bold rounded-full w-4 h-4 flex items-center justify-center shadow-md">
              {alertCount > 9 ? '9+' : alertCount}
            </span>
          )}
        </button>

        <button aria-label="Logout" onClick={onLogout} className="md:hidden p-2 border border-slate-800 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );

  const renderActivePanel = () => {
    switch (tab) {
      case 'overview':
        return <OverviewPanel token={token} serverIP={serverIP} prefs={prefs} />;
      case 'camera':
        return <CameraPanel token={token} serverIP={serverIP} />;
      case 'digitaltwin':
        return <DigitalTwinPanel token={token} serverIP={serverIP} prefs={prefs} />;
      case 'birds':
        return <BirdsPanel token={token} serverIP={serverIP} prefs={prefs} />;
      case 'alerts':
        return <AlertsPanel token={token} serverIP={serverIP} prefs={prefs} />;
      case 'climate':
        return <ClimatePanel token={token} serverIP={serverIP} prefs={prefs} canControlDevices={canControlDevices} />;
      case 'smartops':
        return <SmartOpsPanel serverIP={serverIP} prefs={prefs} token={token} />;
      case 'management':
        return <ManagementPanel token={token} serverIP={serverIP} prefs={prefs} />;
      case 'devices':
        return <DevicesPanel token={token} serverIP={serverIP} prefs={prefs} canControlDevices={canControlDevices} />;
      case 'history':
        return <HistoryPanel token={token} serverIP={serverIP} prefs={prefs} />;
      case 'settings':
        return <SettingsPanel serverIP={serverIP} token={token} prefs={prefs} onSavePrefs={onSavePrefs} onSaveServer={onSaveServer} />;
      case 'admin':
        return <AdminPanel serverIP={serverIP} token={token} />;
      case 'system':
        return <SystemPanel serverIP={serverIP} token={token} />;
      default:
        return <OverviewPanel token={token} serverIP={serverIP} prefs={prefs} />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 flex overflow-hidden">
      {renderDesktopSidebar()}
      {renderMobileSidebar()}

      <main className="flex-1 flex flex-col h-screen relative overflow-hidden">
        {renderHeader()}

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto w-full">
            <div className="mb-6 animate-fade-in-down">
              <h2 className="text-2xl font-extrabold text-white tracking-tight capitalize flex items-center gap-3">
                {currentTab && <currentTab.icon size={24} className="text-emerald-400" />}
                {currentTab?.label || 'Dashboard'}
              </h2>
              <p className="text-slate-500 text-sm mt-1">Gerencie a produção em tempo real.</p>
            </div>

            <div key={tab} className="tab-content-enter">
              {renderActivePanel()}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
