import os

login_screen_code = '''import React, { useState } from 'react';
import { Mail, Lock, Server, ArrowRight, Loader } from 'lucide-react';
import { supabase, isSupabaseConfigured } from '../utils/supabaseClient';
import { getBaseUrl, STORAGE } from '../utils/config';

export default function LoginScreen({ serverIP, setServerIP, onBack, onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [ipForm, setIpForm] = useState(serverIP);
  const [mode, setMode] = useState('login'); // 'login' or 'request'

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    if (ipForm !== serverIP) {
      setServerIP(ipForm);
    }

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
        const { data, error } = await supabase.auth.signUp({
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

        <div className="mt-8 text-center border-t border-slate-800 pt-6">
          <button
            type="button"
            onClick={() => {
              setMode(mode === 'login' ? 'request' : 'login');
              setErrorMsg('');
            }}
            className="text-sm text-slate-400 hover:text-emerald-400 transition-colors font-medium"
          >
            {mode === 'login' ? 'Não tem conta? Solicitar Acesso' : 'Já possui conta? Fazer Login'}
          </button>
        </div>
      </div>
    </div>
  );
}
'''

with open('c:/nic/ChikGuard-Original/frontend/src/pages/LoginScreen.jsx', 'w', encoding='utf-8') as f:
    f.write(login_screen_code)
print("Updated LoginScreen")
