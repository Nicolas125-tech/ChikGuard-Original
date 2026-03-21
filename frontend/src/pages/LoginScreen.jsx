import React, { useState, useEffect } from 'react';
import { ChevronLeft, Settings, Save, User, Key, AlertTriangle, Activity, LogIn } from 'lucide-react';
import { isTunnelHost, getBaseUrl } from '../utils/config';

export default function LoginScreen({ serverIP, setServerIP, onBack, onLogin }) {
  const [accessMode, setAccessMode] = useState('admin');
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
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

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${getBaseUrl(serverIP)}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass }),
      });
      const data = await response.json();
      if (!response.ok) setError(data.msg || 'Credenciais invalidas.');
      else onLogin({ accessToken: data.access_token, role: data.role, username: data.username || user });
    } catch {
      setError('Falha de conexao. Verifique servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900/80 p-6 sm:p-8 rounded-3xl border border-slate-800 relative">
        <button onClick={onBack} className="absolute top-6 left-6 text-slate-500 hover:text-white flex items-center gap-1 text-sm"><ChevronLeft size={16} /> Voltar</button>
        <button onClick={() => setShowConfig((v) => !v)} className="absolute top-6 right-6 text-slate-500 hover:text-emerald-500"><Settings size={20} /></button>

        <div className="text-center mb-8 mt-6 sm:mt-0">
          <h1 className="text-2xl sm:text-3xl font-bold text-white">{accessMode === 'viewer' ? 'Login visitante' : 'Login administrador'}</h1>
          <p className="text-slate-400 text-sm mt-1">{accessMode === 'viewer' ? 'Acesso somente leitura' : 'Acesso seguro'}</p>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-5">
          <button onClick={() => setAccessMode('admin')} className={`py-2 rounded-lg text-sm border ${accessMode === 'admin' ? 'bg-emerald-600/20 border-emerald-500/40 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>Administrador</button>
          <button onClick={() => setAccessMode('viewer')} className={`py-2 rounded-lg text-sm border ${accessMode === 'viewer' ? 'bg-blue-600/20 border-blue-500/40 text-blue-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>Visitante</button>
        </div>

        {showConfig && (
          <div className="mb-6 p-4 bg-slate-950 rounded-xl border border-slate-700">
            <label className="text-xs text-slate-400 uppercase font-bold mb-2 block">Servidor</label>
            <div className="flex gap-2">
              <input value={tempIP} onChange={(e) => setTempIP(e.target.value)} className="flex-1 bg-slate-800 border border-slate-700 text-white p-3 rounded-lg font-mono text-xs focus:border-emerald-500 outline-none w-full" />
              <button onClick={() => { setServerIP(tempIP); setShowConfig(false); }} className="bg-emerald-600 hover:bg-emerald-500 text-white p-3 rounded-lg flex-shrink-0"><Save size={18} /></button>
            </div>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="relative"><User className="absolute left-4 top-3.5 text-slate-500" size={20} /><input type="text" placeholder="Usuario" value={user} onChange={(e) => setUser(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white py-3 pl-12 pr-4 rounded-xl focus:border-emerald-500 outline-none" /></div>
          <div className="relative"><Key className="absolute left-4 top-3.5 text-slate-500" size={20} /><input type="password" placeholder="Senha" value={pass} onChange={(e) => setPass(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white py-3 pl-12 pr-4 rounded-xl focus:border-emerald-500 outline-none" /></div>
          {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-xl text-sm flex items-center justify-center gap-2 text-center"><AlertTriangle size={16} className="flex-shrink-0" /> <span>{error}</span></div>}
          <button disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 rounded-xl flex justify-center items-center gap-2 disabled:opacity-50">{loading ? <Activity className="animate-spin" size={20} /> : <><LogIn size={20} /> Entrar</>}</button>
        </form>
      </div>
    </div>
  );
}
