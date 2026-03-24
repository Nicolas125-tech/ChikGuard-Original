import React, { useState, useEffect, useCallback } from 'react';
import OpeningScreen from './pages/OpeningScreen';
import LandingPage from './pages/LandingPage';
import LoginScreen from './pages/LoginScreen';
import TVScreen from './pages/TVScreen';
import Dashboard from './pages/Dashboard';
import { STORAGE, readPrefs } from './utils/config';

export default function App() {
  const [booting, setBooting] = useState(true);
  const [token, setToken] = useState(localStorage.getItem(STORAGE.token));
  const [role, setRole] = useState(localStorage.getItem(STORAGE.role) || 'admin');
  const [status, setStatus] = useState(localStorage.getItem('cg_status') || 'ACTIVE');
  const [serverIP, setServerIP] = useState(localStorage.getItem(STORAGE.server) || '127.0.0.1');
  const [showLogin, setShowLogin] = useState(false);
  const [prefs, setPrefs] = useState(readPrefs);

  useEffect(() => {
    const t = setTimeout(() => setBooting(false), 1600);
    return () => clearTimeout(t);
  }, []);

  const saveServer = useCallback((value) => {
    const clean = value.replace(/\/$/, '');
    setServerIP(clean);
    localStorage.setItem(STORAGE.server, clean);
  }, []);

  const savePrefs = useCallback((next) => {
    setPrefs(next);
    localStorage.setItem(STORAGE.prefs, JSON.stringify(next));
  }, []);

  const tvMode = window.location.pathname === '/tv';

  if (booting) return <OpeningScreen />;

  if (tvMode) {
    return <TVScreen serverIP={serverIP} />;
  }

  if (token && role === 'viewer') {
    return (
      <TVScreen
        serverIP={serverIP}
        showHeader
        onLogout={() => {
          localStorage.removeItem(STORAGE.token);
          localStorage.removeItem(STORAGE.role);
          localStorage.removeItem('cg_status');
          localStorage.removeItem(STORAGE.username);
          setToken(null);
          setRole('admin');
        }}
      />
    );
  }


  if (token && status === 'PENDING') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800 p-8 rounded-lg shadow-xl max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-emerald-500 mb-4">Aguardando Aprovação</h1>
          <p className="text-slate-300 mb-6">A sua conta foi criada com sucesso, mas precisa de ser aprovada por um administrador antes de aceder ao sistema.</p>
          <button
            onClick={() => {
              localStorage.removeItem(STORAGE.token);
              localStorage.removeItem(STORAGE.role);
              localStorage.removeItem(STORAGE.username);
              localStorage.removeItem('cg_status');
              setToken(null);
              setRole('admin');
              setStatus('ACTIVE');
            }}
            className="w-full bg-slate-700 hover:bg-slate-600 text-white font-bold py-2 px-4 rounded"
          >
            Voltar ao Login
          </button>
        </div>
      </div>
    );
  }

  if (token) {

    return (
      <Dashboard
        token={token}
        role={role}
        serverIP={serverIP}
        prefs={prefs}
        onSavePrefs={savePrefs}
        onSaveServer={saveServer}
        onLogout={() => {
          localStorage.removeItem(STORAGE.token);
          localStorage.removeItem(STORAGE.role);
          localStorage.removeItem('cg_status');
          localStorage.removeItem(STORAGE.username);
          setToken(null);
          setRole('admin');
        }}
      />
    );
  }

  if (showLogin) {
    return (
      <LoginScreen
        serverIP={serverIP}
        setServerIP={saveServer}
        onBack={() => setShowLogin(false)}
        onLogin={({ accessToken, role: nextRole, username: nextUser, status: nextStatus }) => {
          const safeRole = nextRole || 'admin';
          localStorage.setItem(STORAGE.token, accessToken);
          localStorage.setItem(STORAGE.role, safeRole);
          localStorage.setItem(STORAGE.username, nextUser || '');
          setToken(accessToken);
          setRole(safeRole);
          localStorage.setItem('cg_status', nextStatus || 'ACTIVE');
          setStatus(nextStatus || 'ACTIVE');
        }}
      />
    );
  }

  return <LandingPage onLoginClick={() => setShowLogin(true)} />;
}
