import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  ChevronLeft,
  ExternalLink,
  Key,
  LayoutDashboard,
  LogIn,
  LogOut,
  Maximize,
  Save,
  Settings,
  Shield,
  Thermometer,
  User,
  Users,
  WifiOff,
  Wind,
  Zap,
} from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const STORAGE = {
  token: 'cg_token',
  server: 'cg_ip',
  prefs: 'cg_prefs',
};

const DEFAULT_PREFS = {
  statusMs: 3000,
  historyMs: 12000,
  devicesMs: 5000,
  countMs: 3000,
};

const getBaseUrl = (ipOrUrl) => {
  if (window.location.hostname.includes('ngrok')) return window.location.origin;
  if (!ipOrUrl) return 'http://127.0.0.1:5000';
  const clean = ipOrUrl.replace(/\/$/, '');
  if (clean.startsWith('http://') || clean.startsWith('https://')) return clean;
  return `http://${clean}:5000`;
};

const readPrefs = () => {
  try {
    const raw = localStorage.getItem(STORAGE.prefs);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
};

export default function App() {
  const [booting, setBooting] = useState(true);
  const [token, setToken] = useState(localStorage.getItem(STORAGE.token));
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

  if (booting) return <OpeningScreen />;

  if (token) {
    return (
      <Dashboard
        token={token}
        serverIP={serverIP}
        prefs={prefs}
        onSavePrefs={savePrefs}
        onSaveServer={saveServer}
        onLogout={() => {
          localStorage.removeItem(STORAGE.token);
          setToken(null);
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
        onLogin={(accessToken) => {
          localStorage.setItem(STORAGE.token, accessToken);
          setToken(accessToken);
        }}
      />
    );
  }

  return <LandingPage onLoginClick={() => setShowLogin(true)} />;
}

function OpeningScreen() {
  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-8">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-6 w-20 h-20 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
          <Shield size={40} className="text-emerald-400" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">ChickGuard AI</h1>
        <p className="text-slate-400 mt-2">Inicializando sistema...</p>
        <div className="mt-8 h-2 rounded-full bg-slate-800 overflow-hidden">
          <div className="h-full w-full bg-gradient-to-r from-emerald-500 to-blue-500 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

function LandingPage({ onLoginClick }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[120px]" />
      </div>
      <nav className="relative z-10 flex justify-between items-center p-6 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-2">
          <div className="bg-emerald-500/20 p-2 rounded-lg border border-emerald-500/30"><Shield className="text-emerald-500" size={24} /></div>
          <span className="text-xl font-bold tracking-tight">ChickGuard AI</span>
        </div>
        <button onClick={onLoginClick} className="bg-slate-800 hover:bg-slate-700 text-white px-5 py-2 rounded-full font-medium border border-slate-700 hover:border-emerald-500/50 flex items-center gap-2">
          <LogIn size={16} /> Acesso
        </button>
      </nav>
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-4 max-w-5xl mx-auto">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-slate-400">Plataforma profissional para monitoramento da granja</h1>
        <p className="text-lg text-slate-400 max-w-2xl mb-10 leading-relaxed">Tela de abertura, painel em tempo real e configuracoes operacionais centralizadas.</p>
        <button onClick={onLoginClick} className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-4 rounded-xl font-bold text-lg shadow-lg shadow-emerald-500/20 flex items-center gap-2 group">
          Entrar no sistema <ArrowRight className="group-hover:translate-x-1 transition-transform" />
        </button>
      </main>
    </div>
  );
}

function LoginScreen({ serverIP, setServerIP, onBack, onLogin }) {
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [tempIP, setTempIP] = useState(serverIP);

  useEffect(() => {
    if (window.location.hostname.includes('ngrok')) {
      setServerIP(window.location.origin);
      setTempIP(window.location.origin);
    }
  }, [setServerIP]);

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${getBaseUrl(serverIP)}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        body: JSON.stringify({ username: user, password: pass }),
      });
      const data = await response.json();
      if (!response.ok) setError(data.msg || 'Credenciais invalidas.');
      else onLogin(data.access_token);
    } catch {
      setError('Falha de conexao. Verifique servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900/80 p-8 rounded-3xl border border-slate-800 relative">
        <button onClick={onBack} className="absolute top-6 left-6 text-slate-500 hover:text-white flex items-center gap-1 text-sm"><ChevronLeft size={16} /> Voltar</button>
        <button onClick={() => setShowConfig((v) => !v)} className="absolute top-6 right-6 text-slate-500 hover:text-emerald-500"><Settings size={20} /></button>

        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">Login operacional</h1>
          <p className="text-slate-400 text-sm mt-1">Acesso seguro</p>
        </div>

        {showConfig && (
          <div className="mb-6 p-4 bg-slate-950 rounded-xl border border-slate-700">
            <label className="text-xs text-slate-400 uppercase font-bold mb-2 block">Servidor</label>
            <div className="flex gap-2">
              <input value={tempIP} onChange={(e) => setTempIP(e.target.value)} className="flex-1 bg-slate-800 border border-slate-700 text-white p-3 rounded-lg font-mono text-xs focus:border-emerald-500 outline-none" />
              <button onClick={() => { setServerIP(tempIP); setShowConfig(false); }} className="bg-emerald-600 hover:bg-emerald-500 text-white p-3 rounded-lg"><Save size={18} /></button>
            </div>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="relative"><User className="absolute left-4 top-3.5 text-slate-500" size={20} /><input type="text" placeholder="Usuario" value={user} onChange={(e) => setUser(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white py-3 pl-12 pr-4 rounded-xl focus:border-emerald-500 outline-none" /></div>
          <div className="relative"><Key className="absolute left-4 top-3.5 text-slate-500" size={20} /><input type="password" placeholder="Senha" value={pass} onChange={(e) => setPass(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white py-3 pl-12 pr-4 rounded-xl focus:border-emerald-500 outline-none" /></div>
          {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-xl text-sm flex items-center justify-center gap-2"><AlertTriangle size={16} /> {error}</div>}
          <button disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 rounded-xl flex justify-center items-center gap-2 disabled:opacity-50">{loading ? <Activity className="animate-spin" size={20} /> : <><LogIn size={20} /> Entrar</>}</button>
        </form>
      </div>
    </div>
  );
}

function Dashboard({ token, serverIP, prefs, onSavePrefs, onSaveServer, onLogout }) {
  const [tab, setTab] = useState('overview');
  const tabs = useMemo(() => [
    { id: 'overview', label: 'Visao Geral', icon: LayoutDashboard },
    { id: 'settings', label: 'Configuracoes', icon: Settings },
  ], []);

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">
      <header className="bg-slate-900/80 border-b border-slate-800 px-6 h-20 flex justify-between items-center sticky top-0 z-30">
        <div className="flex items-center gap-3"><div className="bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20"><Activity className="text-emerald-500" size={24} /></div><h1 className="text-xl font-bold">ChickGuard AI</h1></div>
        <div className="flex items-center gap-2">
          {tabs.map((item) => {
            const Icon = item.icon;
            return <button key={item.id} onClick={() => setTab(item.id)} className={`px-3 py-2 rounded-lg text-sm border hidden md:flex items-center gap-2 ${tab === item.id ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-slate-900 border-slate-800 text-slate-400'}`}><Icon size={16} /> {item.label}</button>;
          })}
          <button onClick={onLogout} className="ml-2 flex items-center gap-2 text-slate-400 hover:text-red-400"><LogOut size={20} /><span className="hidden sm:inline">Sair</span></button>
        </div>
      </header>
      <main className="flex-1 p-6 max-w-screen-2xl mx-auto w-full">
        {tab === 'overview' ? <OverviewPanel token={token} serverIP={serverIP} prefs={prefs} /> : <SettingsPanel key={`${serverIP}:${prefs.statusMs}:${prefs.historyMs}:${prefs.devicesMs}:${prefs.countMs}`} serverIP={serverIP} prefs={prefs} onSavePrefs={onSavePrefs} onSaveServer={onSaveServer} />}
      </main>
    </div>
  );
}

function OverviewPanel({ token, serverIP, prefs }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(false);
  const [videoBlocked, setVideoBlocked] = useState(false);
  const [historico, setHistorico] = useState([]);
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [contagem, setContagem] = useState(0);

  const baseUrl = getBaseUrl(serverIP);
  const videoUrl = `${baseUrl}/api/video`;

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/status`, { headers: { Authorization: `Bearer ${token}`, 'ngrok-skip-browser-warning': 'true' } });
      if (!r.ok) throw new Error();
      setDados(await r.json());
      setErro(false);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/history`, { headers: { Authorization: `Bearer ${token}`, 'ngrok-skip-browser-warning': 'true' } });
      if (!r.ok) throw new Error('History fetch failed');
      setHistorico(await r.json());
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchDevices = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}`, 'ngrok-skip-browser-warning': 'true' } });
      if (!r.ok) throw new Error('Device state fetch failed');
      setDispositivos(await r.json());
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchCount = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/chick_count`, { headers: { Authorization: `Bearer ${token}`, 'ngrok-skip-browser-warning': 'true' } });
      if (!r.ok) throw new Error('Count fetch failed');
      const data = await r.json();
      setContagem(data.count || 0);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    fetchStatus(); fetchHistory(); fetchDevices(); fetchCount();
    const a = setInterval(fetchStatus, prefs.statusMs);
    const b = setInterval(fetchHistory, prefs.historyMs);
    const c = setInterval(fetchDevices, prefs.devicesMs);
    const d = setInterval(fetchCount, prefs.countMs);
    return () => { clearInterval(a); clearInterval(b); clearInterval(c); clearInterval(d); };
  }, [fetchStatus, fetchHistory, fetchDevices, fetchCount, prefs]);

  const toggleDevice = async (tipo, ligar) => {
    await fetch(`${baseUrl}/api/${tipo}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
      body: JSON.stringify({ ligar }),
    });
    fetchDevices();
  };

  return (
    <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
      <div className="lg:col-span-1 space-y-6">
        <div className="p-6 rounded-2xl border-2 bg-slate-900 border-slate-700">
          <div className="flex items-center gap-2 text-slate-300 font-bold text-xs uppercase tracking-widest mb-4"><Thermometer size={16} /> Temperatura media</div>
          <div className="text-6xl font-bold text-white mb-2 tracking-tighter">{dados ? dados.temperatura : '--'} C</div>
          <div className="inline-block px-3 py-1 rounded-lg font-bold text-sm bg-slate-950/40 border border-white/10">{erro ? 'SEM CONEXAO' : dados?.status || 'CARREGANDO'}</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex justify-between items-start mb-4"><div className="flex items-center gap-2 text-slate-300 font-bold text-xs uppercase tracking-widest"><Users size={16} /> Contagem de aves</div><CheckCircle className="text-emerald-500" size={18} /></div>
          <div className="text-6xl font-bold text-white mb-2 tracking-tighter">{erro ? '--' : contagem}</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <h3 className="text-slate-400 text-xs font-bold uppercase mb-4 flex items-center gap-2 tracking-widest"><LayoutDashboard size={14} /> Historico</h3>
          <div className="h-40">
            {historico.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historico}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="hora" stroke="#64748b" fontSize={10} />
                  <YAxis domain={['dataMin - 2', 'dataMax + 2']} stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
                  <Line type="monotone" dataKey="temp" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981' }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-slate-500 text-sm">Carregando grafico...</div>}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="grid grid-cols-2 gap-4">
            <button onClick={() => toggleDevice('ventilacao', !dispositivos.ventilacao)} className="bg-slate-950 border border-slate-800 p-4 rounded-xl flex flex-col items-center gap-3"><Wind size={22} className="text-blue-400" /><span className="text-sm">Ventilacao</span></button>
            <button onClick={() => toggleDevice('aquecedor', !dispositivos.aquecedor)} className="bg-slate-950 border border-slate-800 p-4 rounded-xl flex flex-col items-center gap-3"><Zap size={22} className="text-orange-400" /><span className="text-sm">Aquecedor</span></button>
          </div>
        </div>
      </div>

      <div className="lg:col-span-2">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden min-h-[400px] relative">
          <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/50 absolute top-0 left-0 right-0 z-20">
            <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm"><Maximize size={16} className="text-slate-500" /> Transmissao da camera</h3>
          </div>
          <div className="relative flex-1 bg-black flex items-center justify-center h-[500px]">
            {erro ? (
              <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-900/50"><WifiOff size={32} className="text-slate-500 mb-3" /><p className="text-slate-400">Sem video</p></div>
            ) : videoBlocked ? (
              <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-900/90 p-8"><AlertTriangle size={48} className="text-yellow-500 mb-4" /><h2 className="text-xl font-bold text-white mb-2">Bloqueio do Ngrok</h2><a href={videoUrl} target="_blank" rel="noreferrer" className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-4 rounded-xl flex items-center gap-2"><ExternalLink size={18} /> Abrir stream</a></div>
            ) : (
              <img src={videoUrl} alt="Visao da Camera" className="w-full h-full object-contain" onError={() => { if (window.location.hostname.includes('ngrok') || serverIP.includes('ngrok')) setVideoBlocked(true); }} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsPanel({ serverIP, prefs, onSavePrefs, onSaveServer }) {
  const [serverDraft, setServerDraft] = useState(serverIP);
  const [draft, setDraft] = useState(prefs);
  const [saved, setSaved] = useState(false);

  const saveAll = () => {
    onSaveServer(serverDraft);
    onSavePrefs({
      statusMs: Number(draft.statusMs) || DEFAULT_PREFS.statusMs,
      historyMs: Number(draft.historyMs) || DEFAULT_PREFS.historyMs,
      devicesMs: Number(draft.devicesMs) || DEFAULT_PREFS.devicesMs,
      countMs: Number(draft.countMs) || DEFAULT_PREFS.countMs,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 1600);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <h2 className="text-xl font-bold flex items-center gap-2"><Settings size={20} /> Configuracoes</h2>
      <p className="text-slate-400 text-sm mt-1">Ajuste conexao com backend e frequencia de atualizacao.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        <Field label="Servidor backend"><input value={serverDraft} onChange={(e) => setServerDraft(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2" /></Field>
        <Field label="Status (ms)"><input type="number" value={draft.statusMs} onChange={(e) => setDraft((p) => ({ ...p, statusMs: e.target.value }))} className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2" /></Field>
        <Field label="Historico (ms)"><input type="number" value={draft.historyMs} onChange={(e) => setDraft((p) => ({ ...p, historyMs: e.target.value }))} className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2" /></Field>
        <Field label="Dispositivos (ms)"><input type="number" value={draft.devicesMs} onChange={(e) => setDraft((p) => ({ ...p, devicesMs: e.target.value }))} className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2" /></Field>
        <Field label="Contagem (ms)"><input type="number" value={draft.countMs} onChange={(e) => setDraft((p) => ({ ...p, countMs: e.target.value }))} className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2" /></Field>
      </div>

      <button onClick={saveAll} className="mt-6 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-5 py-3 rounded-xl flex items-center gap-2"><Save size={16} /> Salvar configuracoes</button>
      {saved && <div className="mt-3 text-sm text-emerald-400 flex items-center gap-2"><CheckCircle size={16} /> Salvo com sucesso.</div>}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="text-sm">
      <span className="block mb-2 text-slate-400">{label}</span>
      {children}
    </label>
  );
}
