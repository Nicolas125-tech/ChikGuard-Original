import React, { useState } from 'react';
import { Mail, Lock, Server, ArrowRight, Loader } from 'lucide-react';
import { supabase, isSupabaseConfigured } from '../utils/supabaseClient';
import { STORAGE } from '../utils/config';

export default function LoginScreen({ onBack, onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [mode, setMode] = useState('login'); // 'login' or 'request'

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
<<<<<<< HEAD
    try {
      const { error } = await supabase.auth.signInWithOAuth({ provider: 'google' });
=======
    setLoading(true);
    setErrorMsg('');
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: import.meta.env.VITE_SITE_URL || window.location.origin
        }
      });
>>>>>>> 89a5f59d53965ec695ea04a566d45cee773d1542
      if (error) throw error;
    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || 'Falha no login com Google');
<<<<<<< HEAD
=======
      setLoading(false);
>>>>>>> 89a5f59d53965ec695ea04a566d45cee773d1542
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
      <div className="absolute top-6 left-6 flex items-center gap-2 cursor-pointer" onClick={onBack}>
         <div className="bg-emerald-500/10 p-1 rounded-lg border border-emerald-500/20 w-8 h-8 flex items-center justify-center">
            <img src="/logo.jpeg" alt="Logo" className="w-5 h-5" />
         </div>
         <span className="text-emerald-400 font-bold tracking-tight">Voltar</span>
      </div>

      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl p-8 transform transition-all">
        <h2 className="text-2xl font-bold text-white text-center tracking-tight mb-2">
            {mode === 'login' ? 'Acesso Restrito' : 'Solicitar Acesso'}
        </h2>
        <p className="text-slate-500 text-center text-sm mb-8">
            {mode === 'login' ? 'Insira suas credenciais corporativas.' : 'Preencha os dados e aguarde a revisão.'}
        </p>

        {errorMsg && (
          <div className={`p-4 rounded-xl text-sm mb-6 flex items-center gap-2 ${errorMsg.includes('enviada') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
            {errorMsg}
          </div>
        )}

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
                className="w-full bg-slate-950 border border-slate-800 text-white rounded-xl focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 pl-11 pr-4 py-3 outline-none transition-colors"
                placeholder="nome@empresa.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Senha</label>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800 text-white rounded-xl focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 pl-11 pr-4 py-3 outline-none transition-colors"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 px-4 rounded-xl transition-colors mt-8"
          >
            {loading ? <Loader className="animate-spin" size={20} /> : (
              <span className="flex items-center gap-2">
                {mode === 'login' ? 'Entrar no Sistema' : 'Enviar Solicitação'} <ArrowRight size={18} />
              </span>
            )}
          </button>
        </form>

<<<<<<< HEAD
        <div className="mt-8 text-center border-t border-slate-800 pt-6 space-y-4">
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-slate-100 text-slate-900 font-bold py-3 px-4 rounded-xl transition-colors shadow-sm"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Entrar com Google
          </button>

=======
        {isSupabaseConfigured && (
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-700"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-slate-900 px-2 text-slate-500 uppercase tracking-wider">ou continuar com</span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={loading}
              className="mt-6 w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-100 text-slate-900 font-semibold py-3 px-4 rounded-xl transition-colors"
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

        <div className="mt-8 text-center border-t border-slate-800 pt-6">
>>>>>>> 89a5f59d53965ec695ea04a566d45cee773d1542
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
