import React, { useState, useEffect } from 'react';
import { ChevronLeft, Settings, Save, User, Key, AlertTriangle, Activity, LogIn, Mail, Plus } from 'lucide-react';
import { isTunnelHost, getBaseUrl } from '../utils/config';
import { supabase, isSupabaseConfigured } from '../utils/supabaseClient';

export default function LoginScreen({ serverIP, setServerIP, onBack, onLogin }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [accessMode, setAccessMode] = useState('admin');
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [tempIP, setTempIP] = useState(serverIP);

  useEffect(() => {
    if (isTunnelHost(window.location.hostname)) {
      setServerIP(window.location.origin);
      setTempIP(window.location.origin);
    }
  }, [setServerIP]);

  useEffect(() => {
    if (accessMode === 'viewer' && !user) setUser('visitante');
  }, [accessMode, user]);

  const handleLegacyLogin = async () => {
    try {
      const response = await fetch(`${getBaseUrl(serverIP)}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass }),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.msg || 'Credenciais inválidas.');
      } else {
        onLogin({
          accessToken: data.access_token,
          role: data.role,
          username: data.username || user,
          status: data.status,
        });
      }
    } catch {
      setError('Falha de conexão. Verifique o servidor.');
    }
  };

  // ─── SIGN UP ────────────────────────────────────────────────────────────────
  const handleSignUp = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMsg('');

    if (!isSupabaseConfigured) {
      setError('Configuração do Supabase está ausente neste ambiente. Contacte o administrador.');
      setLoading(false);
      return;
    }

    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email: user,
        password: pass,
        options: {
          // user_metadata: disponível antes da confirmação de e-mail
          data: { status: 'PENDING', role: 'viewer' },
        },
      });

      if (signUpError) {
        setError(signUpError.message);
        return;
      }

      if (data?.user) {
        // Conta criada — mostrar mensagem e NÃO navegar automaticamente.
        // O utilizador PENDING deve aguardar aprovação do admin.
        setSuccessMsg(
          'Conta criada com sucesso! A sua conta está a aguardar aprovação do administrador. ' +
          'Receberá uma notificação quando for aprovado. Pode agora fazer login.'
        );
        setIsSignUp(false);
        setUser('');
        setPass('');
      } else {
        // Supabase requer confirmação de e-mail (verificar se está ativo no projeto)
        setSuccessMsg('Verifique o seu e-mail para confirmar a conta antes de fazer login.');
      }
    } catch (err) {
      setError(`Erro inesperado: ${err?.message || 'tente novamente.'}`);
    } finally {
      setLoading(false);
    }
  };

  // ─── LOGIN ───────────────────────────────────────────────────────────────────
  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMsg('');

    // Tenta primeiro com Supabase (se configurado e e-mail)
    if (isSupabaseConfigured && user.includes('@')) {
      try {
        const { data, error: signInError } = await supabase.auth.signInWithPassword({
          email: user,
          password: pass,
        });

        if (signInError) {
          // Falha no Supabase → tenta login legacy como fallback
          await handleLegacyLogin();
        } else if (data?.session) {
          let finalRole = String(data.user.app_metadata?.role || 'viewer').toLowerCase();
          let finalStatus = data.user.app_metadata?.status || 'ACTIVE';

          try {
            const { data: profile } = await supabase
              .from('profiles')
              .select('role, status')
              .eq('id', data.user.id)
              .single();
            if (profile) {
              if (profile.role) finalRole = String(profile.role).toLowerCase();
              if (profile.status) finalStatus = profile.status;
            }
          } catch (_) {
            // Profile ainda não criado — manter valores de app_metadata
          }

          onLogin({
            accessToken: data.session.access_token,
            role: finalRole,
            username: data.user.email,
            status: finalStatus,
          });
        }
      } catch {
        await handleLegacyLogin();
      } finally {
        setLoading(false);
      }
    } else {
      // Utilizador sem e-mail (login local/legacy)
      await handleLegacyLogin();
      setLoading(false);
    }
  };

  // ─── OAUTH ───────────────────────────────────────────────────────────────────
  const handleOAuthSignIn = async (provider) => {
    if (!isSupabaseConfigured) {
      setError('Configuração do Supabase ausente para autenticação OAuth.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      // VITE_SITE_URL deve ser definido no .env para dev e nas env vars de produção (Vercel).
      // Isso garante que o redirect aponte SEMPRE para o domínio correto do ChikGuard.
      const redirectTo = import.meta.env.VITE_SITE_URL || window.location.origin;

      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo,
          queryParams: {
            access_type: 'offline',
            prompt: 'consent',
          },
        },
      });
      if (error) setError(error.message);
    } catch (err) {
      setError(`Erro ao iniciar sessão com ${provider}: ${err?.message || 'desconhecido'}`);
    } finally {
      setLoading(false);
    }
  };

  // ─── RENDER ──────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900/80 p-6 sm:p-8 rounded-3xl border border-slate-800 relative">
        <button onClick={onBack} className="absolute top-6 left-6 text-slate-500 hover:text-white flex items-center gap-1 text-sm">
          <ChevronLeft size={16} /> Voltar
        </button>
        <button onClick={() => setShowConfig((v) => !v)} className="absolute top-6 right-6 text-slate-500 hover:text-emerald-500">
          <Settings size={20} />
        </button>

        <div className="text-center mb-8 mt-6 sm:mt-0">
          <h1 className="text-2xl sm:text-3xl font-bold text-white">
            {isSignUp ? 'Criar Conta' : (accessMode === 'viewer' ? 'Login visitante' : 'Login administrador')}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {isSignUp ? 'Registe-se para aceder ao sistema' : (accessMode === 'viewer' ? 'Acesso somente leitura' : 'Acesso seguro')}
          </p>
        </div>

        {!isSignUp && (
          <div className="grid grid-cols-2 gap-2 mb-5">
            <button
              onClick={() => setAccessMode('admin')}
              className={`py-2 rounded-lg text-sm border ${accessMode === 'admin' ? 'bg-emerald-600/20 border-emerald-500/40 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>
              Administrador
            </button>
            <button
              onClick={() => setAccessMode('viewer')}
              className={`py-2 rounded-lg text-sm border ${accessMode === 'viewer' ? 'bg-blue-600/20 border-blue-500/40 text-blue-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>
              Visitante
            </button>
          </div>
        )}

        {showConfig && (
          <div className="mb-6 p-4 bg-slate-950 rounded-xl border border-slate-700">
            <label className="text-xs text-slate-400 uppercase font-bold mb-2 block">Servidor</label>
            <div className="flex gap-2">
              <input
                value={tempIP}
                onChange={(e) => setTempIP(e.target.value)}
                className="flex-1 bg-slate-800 border border-slate-700 text-white p-3 rounded-lg font-mono text-xs focus:border-emerald-500 outline-none w-full"
              />
              <button
                onClick={() => { setServerIP(tempIP); setShowConfig(false); }}
                className="bg-emerald-600 hover:bg-emerald-500 text-white p-3 rounded-lg flex-shrink-0">
                <Save size={18} />
              </button>
            </div>
          </div>
        )}

        {/* Sign Up e Login usam handlers separados para máxima clareza */}
        <form onSubmit={isSignUp ? handleSignUp : handleLogin} className="space-y-4">
          <div className="relative">
            {isSignUp
              ? <Mail className="absolute left-4 top-3.5 text-slate-500" size={20} />
              : <User className="absolute left-4 top-3.5 text-slate-500" size={20} />}
            <input
              type={isSignUp ? 'email' : 'text'}
              placeholder={isSignUp ? 'E-mail' : 'Usuário ou E-mail'}
              value={user}
              onChange={(e) => setUser(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white py-3 pl-12 pr-4 rounded-xl focus:border-emerald-500 outline-none"
              required
            />
          </div>
          <div className="relative">
            <Key className="absolute left-4 top-3.5 text-slate-500" size={20} />
            <input
              type="password"
              placeholder="Senha"
              value={pass}
              onChange={(e) => setPass(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white py-3 pl-12 pr-4 rounded-xl focus:border-emerald-500 outline-none"
              required
              minLength={isSignUp ? 6 : 1}
            />
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-xl text-sm flex items-center justify-center gap-2 text-center">
              <AlertTriangle size={16} className="flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {successMsg && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-3 rounded-xl text-sm flex items-center justify-center gap-2 text-center">
              <span>{successMsg}</span>
            </div>
          )}

          <button
            disabled={loading}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 rounded-xl flex justify-center items-center gap-2 disabled:opacity-50 transition-colors">
            {loading
              ? <Activity className="animate-spin" size={20} />
              : isSignUp
                ? <><Plus size={20} /> Criar Conta</>
                : <><LogIn size={20} /> Entrar</>}
          </button>
        </form>

        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-slate-900/80 text-slate-500">Ou continue com</span>
            </div>
          </div>

          <div className="mt-6 flex justify-center">
            <button
              type="button"
              onClick={() => handleOAuthSignIn('google')}
              disabled={loading}
              className="w-full flex justify-center items-center gap-2 bg-white hover:bg-slate-100 text-slate-900 font-semibold py-3 px-4 rounded-xl border border-slate-200 transition-colors">
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Google
            </button>
          </div>
        </div>

        <div className="mt-8 text-center text-sm text-slate-500">
          {isSignUp ? (
            <p>
              Já tem uma conta?{' '}
              <button
                onClick={() => { setIsSignUp(false); setError(''); setSuccessMsg(''); }}
                className="text-emerald-500 hover:text-emerald-400 font-medium transition-colors">
                Fazer login
              </button>
            </p>
          ) : (
            <p>
              Não tem uma conta?{' '}
              <button
                onClick={() => { setIsSignUp(true); setError(''); setSuccessMsg(''); }}
                className="text-emerald-500 hover:text-emerald-400 font-medium transition-colors">
                Criar agora
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
