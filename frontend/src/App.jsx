import React, { useState, useEffect, useCallback } from 'react';
import OpeningScreen from './pages/OpeningScreen';
import LandingPage from './pages/LandingPage';
import LoginScreen from './pages/LoginScreen';
import TVScreen from './pages/TVScreen';
import Dashboard from './pages/Dashboard';
import { STORAGE, readPrefs } from './utils/config';
import { supabase, isSupabaseConfigured } from './utils/supabaseClient';

// ─── Error Boundary ───────────────────────────────────────────────────────────
// Captura qualquer erro de renderização não tratado e exibe uma tela de
// recuperação em vez de deixar a aplicação com tela branca.
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[ChikGuard] Crash capturado pelo ErrorBoundary:', error, info?.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-red-500/30 p-8 rounded-2xl max-w-md w-full text-center shadow-xl">
            <div className="bg-red-500/10 rounded-full p-4 w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-red-400 mb-2">Erro Inesperado</h1>
            <p className="text-slate-400 mb-2 text-sm">
              Ocorreu um erro crítico na aplicação.
            </p>
            {this.state.error?.message && (
              <p className="text-slate-500 text-xs font-mono bg-slate-950 p-3 rounded-lg mb-6 text-left break-all">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-xl transition-colors">
              Recarregar a Aplicação
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── App principal ────────────────────────────────────────────────────────────
function AppCore() {
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

  // Corrigir cache stale: admin/superadmin nunca devem ficar em PENDING
  useEffect(() => {
    const cachedRole = localStorage.getItem(STORAGE.role) || '';
    const cachedStatus = localStorage.getItem('cg_status') || '';
    if (['superadmin', 'admin'].includes(cachedRole) && cachedStatus === 'PENDING') {
      localStorage.setItem('cg_status', 'ACTIVE');
      setStatus('ACTIVE');
    }
  }, []);

  // Listener do Supabase Auth (OAuth redirect, session refresh, etc.)
  useEffect(() => {
    if (!isSupabaseConfigured) return;

    const { data: authListener } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        let accessToken = session.access_token;
        let nextRole = String(session.user.app_metadata?.role || 'viewer').toLowerCase();
        let nextUser = session.user.email;
        // Default: ACTIVE (PENDING somente quando profile diz explicitamente)
        let nextStatus = 'ACTIVE';

        // Buscar role/status real da tabela profiles
        try {
          const { data: profile } = await supabase
            .from('profiles')
            .select('role, status')
            .eq('id', session.user.id)
            .single();
          if (profile) {
            if (profile.role) nextRole = String(profile.role).toLowerCase();
            if (profile.status) nextStatus = profile.status;
          }
        } catch {
          // Profile ainda não existe — usar valores padrão
        }

        // Superadmin e admin são sempre ACTIVE, nunca ficam em PENDING
        if (['superadmin', 'admin'].includes(nextRole)) {
          nextStatus = 'ACTIVE';
        }

        localStorage.setItem(STORAGE.token, accessToken);
        localStorage.setItem(STORAGE.role, nextRole);
        localStorage.setItem(STORAGE.username, nextUser || '');
        localStorage.setItem('cg_status', nextStatus);

        setToken(accessToken);
        setRole(nextRole);
        setStatus(nextStatus);
        setShowLogin(false);
      } else if (event === 'SIGNED_OUT') {
        localStorage.removeItem(STORAGE.token);
        localStorage.removeItem(STORAGE.role);
        localStorage.removeItem(STORAGE.username);
        localStorage.removeItem('cg_status');
        setToken(null);
        setRole('admin');
        setStatus('ACTIVE');
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
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

  const handleLogout = async () => {
    if (isSupabaseConfigured) {
      try {
        await supabase.auth.signOut();
      } catch (err) {
        console.error('Erro ao fazer signOut do Supabase:', err);
      }
    }
    localStorage.removeItem(STORAGE.token);
    localStorage.removeItem(STORAGE.role);
    localStorage.removeItem('cg_status');
    localStorage.removeItem(STORAGE.username);
    setToken(null);
    setRole('admin');
    setStatus('ACTIVE');
    setShowLogin(false);
  };

  const tvMode = window.location.pathname === '/tv';

  if (booting) return <OpeningScreen />;

  if (tvMode) return <TVScreen serverIP={serverIP} />;

  if (token && status === 'PENDING') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800 p-8 rounded-2xl shadow-xl max-w-md w-full text-center border border-slate-700">
          <div className="bg-amber-500/10 rounded-full p-4 w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-emerald-500 mb-3">Aguardando Aprovação</h1>
          <p className="text-slate-300 mb-6 text-sm leading-relaxed">
            A sua conta foi criada com sucesso, mas precisa de ser aprovada por um administrador antes de aceder ao sistema.
            Receberá uma notificação por e-mail quando for aprovado.
          </p>
          <button
            onClick={handleLogout}
            className="w-full bg-slate-700 hover:bg-slate-600 text-white font-bold py-3 px-4 rounded-xl transition-colors">
            Sair e Voltar ao Login
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
        onLogout={handleLogout}
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
          const safeRole = String(nextRole || 'admin').toLowerCase();
          localStorage.setItem(STORAGE.token, accessToken);
          localStorage.setItem(STORAGE.role, safeRole);
          localStorage.setItem(STORAGE.username, nextUser || '');
          localStorage.setItem('cg_status', nextStatus || 'ACTIVE');
          setToken(accessToken);
          setRole(safeRole);
          setStatus(nextStatus || 'ACTIVE');
        }}
      />
    );
  }

  return <LandingPage onLoginClick={() => setShowLogin(true)} />;
}

// Envolvemos AppCore com ErrorBoundary para capturar qualquer crash de renderização
export default function App() {
  return (
    <ErrorBoundary>
      <AppCore />
    </ErrorBoundary>
  );
}
