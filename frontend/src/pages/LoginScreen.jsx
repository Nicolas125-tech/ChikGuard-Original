import React, { useState } from 'react';
import { Mail, Lock, ArrowRight, Loader, Eye, EyeOff } from 'lucide-react';
import { supabase, isSupabaseConfigured } from '../utils/supabaseClient';
import { STORAGE } from '../utils/config';

export default function LoginScreen({ onBack, onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [mode, setMode] = useState('login');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    try {
      if (mode === 'login') {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password
        });
        if (error) throw error;
        
        let role = 'viewer';
        let status = 'PENDING';
        if (data.session) {
           const { data: profile } = await supabase.from('profiles').select('role, status').eq('id', data.session.user.id).single();
           if (profile) {
              role = profile.role || role;
              status = profile.status || status;
           }
           onLogin({ accessToken: data.session.access_token, role, username: email, status });
        }
      } else {
        const { error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        
        setErrorMsg('Solicitação enviada. Aguarde aprovação de um Administrador.');
        setMode('login');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || 'Falha na autenticação');
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
        options: {
          redirectTo: import.meta.env.VITE_SITE_URL || window.location.origin
        }
      });
      if (error) throw error;
    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || 'Falha no login com Google');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-grid-pattern opacity-40"></div>
      <div className="absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-emerald-500/8 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-0 right-0 w-[300px] h-[300px] rounded-full bg-blue-600/5 blur-[100px] pointer-events-none"></div>

      {/* Back Button */}
      <div className="absolute top-6 left-6 flex items-center gap-2 cursor-pointer z-10 group" onClick={onBack}>
         <div className="bg-emerald-500/10 p-1.5 rounded-lg border border-emerald-500/20 w-8 h-8 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
            <img src="/logo.jpeg" alt="Logo" className="w-5 h-5" />
         </div>
         <span className="text-emerald-400 font-bold tracking-tight group-hover:text-emerald-300 transition-colors">Voltar</span>
      </div>

      {/* Login Card */}
      <div className="w-full max-w-md glass rounded-3xl shadow-2xl p-8 animate-scale-in relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-5 animate-float">
            <img src="/logo.jpeg" alt="ChikGuard" className="w-9 h-9 object-contain rounded-lg" />
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight mb-1">
              {mode === 'login' ? 'Acesso Restrito' : 'Solicitar Acesso'}
          </h2>
          <p className="text-slate-500 text-sm">
              {mode === 'login' ? 'Insira suas credenciais corporativas.' : 'Preencha os dados e aguarde a revisão.'}
          </p>
        </div>

        {/* Error/Success Messages */}
        {errorMsg && (
          <div className={`p-4 rounded-xl text-sm mb-6 flex items-center gap-2 animate-fade-in-down ${errorMsg.includes('enviada') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
            {errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Email</label>
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full bg-slate-950/80 border border-slate-800 text-white rounded-xl focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/50 pl-11 pr-4 py-3.5 outline-none transition-all placeholder:text-slate-600"
                placeholder="nome@empresa.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Senha</label>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full bg-slate-950/80 border border-slate-800 text-white rounded-xl focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/50 pl-11 pr-12 py-3.5 outline-none transition-all placeholder:text-slate-600"
                placeholder="••••••••"
              />
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShowPassword(v => !v)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 px-4 rounded-xl transition-all mt-8 hover-lift shadow-lg shadow-emerald-500/20 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? <Loader className="animate-spin" size={20} /> : (
              <span className="flex items-center gap-2">
                {mode === 'login' ? 'Entrar no Sistema' : 'Enviar Solicitação'} <ArrowRight size={18} />
              </span>
            )}
          </button>
        </form>

        {/* Google OAuth */}
        {isSupabaseConfigured && (
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-700/60"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-transparent px-3 text-slate-500 uppercase tracking-wider glass-light rounded-full py-0.5">ou continuar com</span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={loading}
              className="mt-5 w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-100 text-slate-900 font-semibold py-3 px-4 rounded-xl transition-all hover-lift shadow-md disabled:opacity-60"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Google
            </button>
          </div>
        )}

        {/* Toggle Mode */}
        <div className="mt-8 text-center border-t border-slate-800/60 pt-6">
          <button
            type="button"
            onClick={() => {
              setMode(mode === 'login' ? 'request' : 'login');
              setErrorMsg('');
            }}
            className="text-sm text-slate-400 hover:text-emerald-400 transition-colors font-medium block w-full"
          >
            {mode === 'login' ? 'Não tem conta? Solicitar Acesso' : 'Já possui conta? Fazer Login'}
          </button>
        </div>
      </div>
    </div>
  );
}
