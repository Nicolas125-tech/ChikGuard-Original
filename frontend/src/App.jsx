import React, { useState, useEffect, useCallback } from 'react';
import OpeningScreen from '@/pages/OpeningScreen';
import LandingPage from '@/pages/LandingPage';
import LoginScreen from '@/pages/LoginScreen';
import TVScreen from '@/pages/TVScreen';
import Dashboard from '@/pages/Dashboard';
import ProtectedRoute from '@/components/ProtectedRoute';
import { STORAGE, readPrefs } from '@/utils/config';
import { supabase, isSupabaseConfigured } from '@/utils/supabaseClient';
import { Toaster } from 'sonner';

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
  const [role, setRole] = useState(localStorage.getItem(STORAGE.role) || 'viewer');
  const [status, setStatus] = useState(localStorage.getItem('cg_status') || 'PENDING');
  const [serverIP, setServerIP] = useState(localStorage.getItem(STORAGE.server) || '127.0.0.1');
  const [showLogin, setShowLogin] = useState(false);
  const [prefs, setPrefs] = useState(readPrefs);

  // Fetch initial session and delay booting
  // CRITICAL: Always re-fetch the real profile from Supabase on boot
  // to avoid stale PENDING status from previous sessions in localStorage.
  useEffect(() => {
    const hasAuthCallback = (window.location.hash && window.location.hash.includes('access_token')) || 
                            (window.location.search && window.location.search.includes('code='));
    
    if (hasAuthCallback) {
      // Se tivermos na URL de callback do OAuth (Google), damos mais tempo
      // para o Supabase processar a troca de código/token em background
      setTimeout(() => setBooting(false), 4000);
      return;
    }

    // Normal boot: busca sessão e perfil do Supabase (com timeout)
    const checkSession = async () => {
      if (isSupabaseConfigured) {
        try {
          const { data: sessionData } = await Promise.race([
            supabase.auth.getSession(),
            new Promise((_, reject) => setTimeout(() => reject(new Error('Session Timeout')), 8000))
          ]);

          if (sessionData?.session) {
            const session = sessionData.session;
            localStorage.setItem(STORAGE.token, session.access_token);
            setToken(session.access_token);

            // Busca perfil com timeout de 4s — não bloqueia a boot se Supabase estiver lento
            try {
              const { data: profile } = await Promise.race([
                supabase.from('profiles').select('role, status').eq('id', session.user.id).single(),
                new Promise((_, reject) => setTimeout(() => reject(new Error('Profile Timeout')), 4000))
              ]);

              if (profile) {
                const realRole   = (profile.role   || 'viewer').toLowerCase();
                const realStatus = profile.status  || 'ACTIVE';
                localStorage.setItem(STORAGE.role,    realRole);
                localStorage.setItem('cg_status',     realStatus);
                setRole(realRole);
                setStatus(realStatus);
              }
              // Se profile === null (tabela vazia), mantém o que já estava no localStorage
            } catch {
              // Profile fetch timeout/RLS → usa valores do localStorage (já setados acima)
            }
          }
        } catch (e) {
          console.error('Erro ao conectar ao Supabase:', e);
        }
      }
      setTimeout(() => setBooting(false), 400);
    };
    checkSession();
  }, []);


  // Listener do Supabase Auth (OAuth redirect, session refresh, etc.)
  useEffect(() => {
    if (!isSupabaseConfigured) return;

    const { data: authListener } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        const accessToken = session.access_token;
        let nextRole   = 'viewer';
        let nextUser   = session.user.email;
        let nextStatus = 'ACTIVE'; // default seguro — não bloqueia se perfil não existir

        // Busca role/status com timeout de 4s — não bloqueia o login
        try {
          const { data: profile } = await Promise.race([
            supabase.from('profiles').select('role, status').eq('id', session.user.id).single(),
            new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 4000))
          ]);
          if (profile) {
            nextRole   = (profile.role   || 'viewer').toLowerCase();
            nextStatus = profile.status  || 'ACTIVE';
          }
        } catch {
          // Timeout ou RLS → usa defaults seguros
        }

        if (nextStatus === 'PENDING' || nextStatus === 'SUSPENDED' || nextStatus === 'REJECTED') {
          await supabase.auth.signOut();
          localStorage.removeItem(STORAGE.token);
          localStorage.removeItem(STORAGE.role);
          localStorage.removeItem(STORAGE.username);
          localStorage.removeItem('cg_status');
          setToken(null);
          setRole('viewer');
          setStatus(nextStatus);
          setShowLogin(true);
          setBooting(false);
          return;
        }

        localStorage.setItem(STORAGE.token,    accessToken);
        localStorage.setItem(STORAGE.role,     nextRole);
        localStorage.setItem(STORAGE.username, nextUser || '');
        localStorage.setItem('cg_status',      nextStatus);

        setToken(accessToken);
        setRole(nextRole);
        setStatus(nextStatus);
        setShowLogin(false);
        setBooting(false);
      } else if (event === 'SIGNED_OUT') {
        localStorage.removeItem(STORAGE.token);
        localStorage.removeItem(STORAGE.role);
        localStorage.removeItem(STORAGE.username);
        localStorage.removeItem('cg_status');
        setToken(null);
        setRole('viewer');
        setStatus('PENDING');
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

  const handleLogout = () => {
    // Limpa estado IMEDIATAMENTE — não espera o Supabase responder
    localStorage.removeItem(STORAGE.token);
    localStorage.removeItem(STORAGE.role);
    localStorage.removeItem('cg_status');
    localStorage.removeItem(STORAGE.username);
    setToken(null);
    setRole('viewer');
    setStatus('PENDING');
    setShowLogin(false);

    // Chama signOut do Supabase em background (não bloqueia a UI)
    if (isSupabaseConfigured) {
      supabase.auth.signOut().catch(err =>
        console.warn('[logout] Supabase signOut falhou (ignorado):', err)
      );
    }
  };

  const tvMode = window.location.pathname === '/tv';

  if (booting) return <OpeningScreen />;

  if (tvMode) return <TVScreen serverIP={serverIP} />;

  if (token) {
    return (
      <ProtectedRoute token={token} userRole={role} status={status} onLogout={handleLogout}>
        <Dashboard
          token={token}
          role={role}
          serverIP={serverIP}
          prefs={prefs}
          onSavePrefs={savePrefs}
          onSaveServer={saveServer}
          onLogout={handleLogout}
        />
      </ProtectedRoute>
    );
  }

  if (showLogin) {
    return (
      <LoginScreen
        serverIP={serverIP}
        setServerIP={saveServer}
        onBack={() => setShowLogin(false)}
        onLogin={({ accessToken, role: nextRole, username: nextUser, status: nextStatus }) => {
          const safeRole = String(nextRole || 'viewer').toLowerCase();
          localStorage.setItem(STORAGE.token, accessToken);
          localStorage.setItem(STORAGE.role, safeRole);
          localStorage.setItem(STORAGE.username, nextUser || '');
          localStorage.setItem('cg_status', nextStatus || 'PENDING');
          setToken(accessToken);
          setRole(safeRole);
          setStatus(nextStatus || 'PENDING');
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
      <Toaster theme="dark" position="top-right" richColors toastOptions={{ style: { background: '#0f172a', borderColor: '#1e293b' } }} />
      <AppCore />
    </ErrorBoundary>
  );
}
