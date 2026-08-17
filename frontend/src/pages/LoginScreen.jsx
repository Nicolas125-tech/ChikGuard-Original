import React, { useState } from 'react';
import { Mail, Lock, ArrowRight, Loader, Eye, EyeOff, Globe, ChevronDown } from 'lucide-react';
import { supabase } from '../utils/supabaseClient';

export default function LoginScreen({ onBack, onLogin, serverIP, setServerIP }) {
  const [email, setEmail]               = useState('');
  const [password, setPassword]         = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading]           = useState(false);
  const [errorMsg, setErrorMsg]         = useState('');
  const [server, setServer]             = useState(serverIP || localStorage.getItem('cg_ip') || '');
  const [showServer, setShowServer]     = useState(false);

  // ── Busca perfil com timeout de 5 s (não bloqueia o login se demorar) ──
  const fetchProfileSafe = async (userId) => {
    try {
      const result = await Promise.race([
        supabase.from('profiles').select('role, status').eq('id', userId).single(),
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000)),
      ]);
      return result?.data || null;
    } catch {
      return null; // timeout/RLS → trata como sem perfil
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;

      if (data.session) {
        // Tenta ler a role do perfil — se não existir ou demorar, usa viewer/ACTIVE
        const profile = await fetchProfileSafe(data.session.user.id);
        const role    = (profile?.role || 'viewer').toLowerCase();
        const status  = profile?.status || 'ACTIVE';

        // Verifica o status de aprovação da conta
        if (status === 'PENDING') {
          await supabase.auth.signOut();
          setErrorMsg('⏳ Sua conta foi criada, mas aguarda a aprovação de um administrador da granja.');
          return;
        }
        if (status === 'SUSPENDED') {
          await supabase.auth.signOut();
          setErrorMsg('🔒 Conta suspensa. Contacte o administrador do sistema.');
          return;
        }
        if (status === 'REJECTED') {
          await supabase.auth.signOut();
          setErrorMsg('❌ Acesso negado. Contacte o suporte.');
          return;
        }

        onLogin({
          accessToken: data.session.access_token,
          role,
          username: profile?.full_name || email,
          status: 'ACTIVE',
        });
      }
    } catch (err) {
      console.error(err);
      const msg = err.message || '';
      if (msg.includes('Invalid login credentials') || msg.includes('invalid_credentials')) {
        setErrorMsg('Credenciais inválidas ou conta não aprovada.');
      } else if (msg.includes('Email not confirmed')) {
        setErrorMsg('Confirme seu e-mail antes de fazer login. Verifique sua caixa de entrada.');
      } else {
        setErrorMsg(msg || 'Falha na autenticação. Tente novamente.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: import.meta.env.VITE_SITE_URL || window.location.origin }
      });
      if (error) throw error;
    } catch (err) {
      setErrorMsg(err.message || 'Falha no login com Google');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-grid-pattern opacity-40" />
      <div className="absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-emerald-500/8 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[300px] h-[300px] rounded-full bg-blue-600/5 blur-[100px] pointer-events-none" />

      {/* Voltar */}
      <button
        className="absolute top-6 left-6 flex items-center gap-2 cursor-pointer z-10 group focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 focus:outline-none rounded-lg p-1"
        onClick={onBack}
        aria-label="Voltar para a página anterior"
      >
        <div className="bg-emerald-500/10 p-1.5 rounded-lg border border-emerald-500/20 w-8 h-8 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
          <img src="/logo.jpeg" alt="Logo" className="w-5 h-5" />
        </div>
        <span className="text-emerald-400 font-bold tracking-tight group-hover:text-emerald-300 transition-colors">Voltar</span>
      </button>

      {/* Card */}
      <div className="w-full max-w-md glass rounded-3xl shadow-2xl p-8 animate-scale-in relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-5 animate-float">
            <img src="/logo.jpeg" alt="ChikGuard" className="w-10 h-10 object-contain rounded-xl" />
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight mb-1">Entrar no Sistema</h2>
          <p className="text-slate-500 text-sm">Insira suas credenciais para acessar o painel.</p>
        </div>

        {/* Mensagem de erro */}
        {errorMsg && (
          <div className={`p-4 rounded-xl text-sm mb-6 flex items-start gap-3 animate-fade-in-down leading-relaxed ${
            errorMsg.startsWith('🔒') || errorMsg.startsWith('❌')
              ? 'bg-red-500/10 text-red-300 border border-red-500/20'
              : 'bg-red-500/10 text-red-300 border border-red-500/20'
          }`}>
            {errorMsg}
          </div>
        )}

        {/* Formulário */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">
              E-mail
            </label>
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full bg-slate-950/80 border border-slate-800 text-white rounded-xl focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/50 pl-11 pr-4 py-3.5 outline-none transition-all placeholder:text-slate-600"
                placeholder="nome@empresa.com"
              />
            </div>
          </div>

          {/* Senha */}
          <div>
            <label htmlFor="password" className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">
              Senha
            </label>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="w-full bg-slate-950/80 border border-slate-800 text-white rounded-xl focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/50 pl-11 pr-12 py-3.5 outline-none transition-all placeholder:text-slate-600"
                placeholder="••••••••"
              />
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShowPassword(v => !v)}
                aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Servidor (colapsável) */}
          <div>
            <button
              type="button"
              onClick={() => setShowServer(v => !v)}
              aria-expanded={showServer}
              className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2 hover:text-slate-300 transition-colors"
            >
              <Globe size={13} />
              Servidor / Tunnel
              <ChevronDown size={13} className={`transition-transform ${showServer ? 'rotate-180' : ''}`} />
            </button>
            {showServer && (
              <div className="relative animate-fade-in-down">
                <Globe className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input
                  aria-label="Endereço do servidor"
                  type="text"
                  value={server}
                  onChange={e => {
                    setServer(e.target.value);
                    localStorage.setItem('cg_ip', e.target.value);
                    if (setServerIP) setServerIP(e.target.value);
                  }}
                  className="w-full bg-slate-950/80 border border-slate-800 text-white rounded-xl focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/50 pl-11 pr-4 py-3.5 outline-none transition-all placeholder:text-slate-600 text-sm"
                  placeholder="ex: abc123.trycloudflare.com ou 192.168.1.100"
                />
                <p className="text-[10px] text-slate-600 mt-1.5 pl-1">Cole o link do Cloudflare Tunnel ou IP do servidor backend.</p>
              </div>
            )}
          </div>

          {/* Botão */}
          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 px-4 rounded-xl transition-all mt-4 shadow-lg shadow-emerald-500/20 disabled:opacity-60 disabled:cursor-not-allowed hover-lift"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <Loader className="animate-spin" size={18} />
                Autenticando…
              </span>
            ) : (
              <span className="flex items-center gap-2">
                Entrar no Sistema <ArrowRight size={18} />
              </span>
            )}
          </button>

          {loading && (
            <p className="text-center text-xs text-slate-600 animate-pulse">
              Verificando credenciais… pode levar alguns segundos.
            </p>
          )}
        </form>

        {/* Google */}
        <div className="mt-6">
          <div className="relative mb-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800/70" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-slate-900/80 px-3 text-slate-500 uppercase tracking-wider rounded-full py-0.5">
                ou continuar com
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-100 text-slate-900 font-semibold py-3 px-4 rounded-xl transition-all hover-lift shadow-md disabled:opacity-60"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Entrar com Google
          </button>
        </div>
      </div>
    </div>
  );
}
