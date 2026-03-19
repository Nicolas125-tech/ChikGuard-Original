import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bell,
  CheckCircle,
  ChevronLeft,
  Cpu,
  Database,
  ExternalLink,
  History,
  Key,
  LayoutDashboard,
  LogIn,
  LogOut,
  Maximize,
  Save,
  Settings,
  SlidersHorizontal,
  Thermometer,
  User,
  Users,
  WifiOff,
  Wind,
  Zap,
} from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { io } from 'socket.io-client';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import * as XLSX from 'xlsx';

const STORAGE = {
  token: 'cg_token',
  role: 'cg_role',
  username: 'cg_username',
  server: 'cg_ip',
  prefs: 'cg_prefs',
};

const DEFAULT_PREFS = {
  statusMs: 3000,
  historyMs: 12000,
  devicesMs: 5000,
  countMs: 3000,
};

const isTunnelHost = (value = '') => /trycloudflare|cfargotunnel/i.test(value);

const getBaseUrl = (ipOrUrl) => {
  if (isTunnelHost(window.location.hostname)) return window.location.origin;
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

function WebRTCVideo({ url, className, onConnectionStateChange }) {
  const videoRef = useRef(null);
  const callbackRef = useRef(onConnectionStateChange);

  useEffect(() => {
    callbackRef.current = onConnectionStateChange;
  }, [onConnectionStateChange]);

  useEffect(() => {
    const config = {
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    };
    let pc = new RTCPeerConnection(config);

    const startWebRTC = async () => {
      pc.addTransceiver('video', { direction: 'recvonly' });

      pc.addEventListener('track', (evt) => {
        if (evt.track.kind === 'video') {
          if (videoRef.current) {
            videoRef.current.srcObject = evt.streams[0];
          }
        }
      });

      pc.addEventListener('connectionstatechange', () => {
        console.log('WebRTC connection state:', pc.connectionState);
        if (callbackRef.current) {
          callbackRef.current(pc.connectionState);
        }
      });

      try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        // Wait for ICE gathering to complete before sending the offer
        await new Promise((resolve) => {
          if (pc.iceGatheringState === 'complete') {
            resolve();
          } else {
            const checkState = () => {
              if (pc.iceGatheringState === 'complete') {
                pc.removeEventListener('icegatheringstatechange', checkState);
                resolve();
              }
            };
            pc.addEventListener('icegatheringstatechange', checkState);
            // Fallback timeout just in case it takes too long
            setTimeout(() => {
              pc.removeEventListener('icegatheringstatechange', checkState);
              resolve();
            }, 3000);
          }
        });

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sdp: pc.localDescription.sdp,
            type: pc.localDescription.type,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to send WebRTC offer');
        }

        const answer = await response.json();
        await pc.setRemoteDescription(answer);
      } catch (err) {
        console.error('WebRTC negotiation error:', err);
      }
    };

    startWebRTC();

    return () => {
      pc.close();
    };
  }, [url]);

  return <video ref={videoRef} className={className} autoPlay playsInline muted />;
}

export default function App() {
  const [booting, setBooting] = useState(true);
  const [token, setToken] = useState(localStorage.getItem(STORAGE.token));
  const [role, setRole] = useState(localStorage.getItem(STORAGE.role) || 'admin');
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
          localStorage.removeItem(STORAGE.username);
          setToken(null);
          setRole('admin');
        }}
      />
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
        onLogin={({ accessToken, role: nextRole, username: nextUser }) => {
          const safeRole = nextRole || 'admin';
          localStorage.setItem(STORAGE.token, accessToken);
          localStorage.setItem(STORAGE.role, safeRole);
          localStorage.setItem(STORAGE.username, nextUser || '');
          setToken(accessToken);
          setRole(safeRole);
        }}
      />
    );
  }

  return <LandingPage onLoginClick={() => setShowLogin(true)} />;
}

function TVScreen({ serverIP, showHeader = false, onLogout }) {
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [weather, setWeather] = useState(null);
  const baseUrl = getBaseUrl(serverIP);
  const videoUrl = `${baseUrl}/api/video`;

  const load = useCallback(async () => {
    const [s, a, w] = await Promise.all([
      fetch(`${baseUrl}/api/summary`),
      fetch(`${baseUrl}/api/alerts`),
      fetch(`${baseUrl}/api/weather/forecast`),
    ]);
    if (s.ok) setSummary(await s.json());
    if (a.ok) setAlerts(await a.json());
    if (w.ok) setWeather(await w.json());
  }, [baseUrl]);

  useEffect(() => {
    const bootstrap = setTimeout(load, 0);
    const timer = setInterval(load, 4000);

    // WebSocket listener for instant updates
    const socket = io(baseUrl);
    socket.on('new_alert', (data) => {
      console.log('Socket event received (TVScreen):', data);
      load();
    });

    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
      socket.disconnect();
    };
  }, [load, baseUrl]);

  return (
    <div className="min-h-screen bg-black text-white">
      {showHeader && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950">
          <div className="font-bold text-lg">ChikGuard Visitante</div>
          <button onClick={onLogout} className="text-sm text-slate-300 hover:text-white">Sair</button>
        </div>
      )}
      <div className="p-6">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-slate-950 border border-slate-800 rounded-3xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 text-2xl font-bold">ChikGuard TV</div>
          <img src={videoUrl} alt="Camera TV" className="w-full h-[70vh] object-contain bg-black" />
        </div>
        <div className="space-y-4">
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4">
            <div className="text-xs uppercase text-slate-400">Temperatura</div>
            <div className="text-6xl font-black">{summary?.temperatura_atual ?? '--'}C</div>
            <div className="text-2xl mt-1">{summary?.status_atual || '--'}</div>
            <div className="text-sm text-slate-400 mt-2">Conforto: {summary?.comfort_score ?? '--'}/100</div>
          </div>
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4">
            <div className="text-xs uppercase text-slate-400">Previsao</div>
            <div className="text-lg">{weather?.message || 'Sem previsao'}</div>
          </div>
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 max-h-72 overflow-auto">
            <div className="text-xs uppercase text-slate-400 mb-2">Alertas</div>
            {(alerts || []).slice(0, 8).map((al) => (
              <div key={al.id} className="py-2 border-b border-slate-800">
                <div className="font-semibold text-lg">{al.tipo}</div>
                <div className="text-sm text-slate-300">{al.mensagem}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

function OpeningScreen() {
  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-8">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-6 w-24 h-24 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center overflow-hidden">
          <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-20 h-20 object-contain" />
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
          <div className="bg-emerald-500/10 p-1 rounded-lg border border-emerald-500/30 w-11 h-11 flex items-center justify-center overflow-hidden">
            <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-8 h-8 object-contain" />
          </div>
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
      <div className="w-full max-w-md bg-slate-900/80 p-8 rounded-3xl border border-slate-800 relative">
        <button onClick={onBack} className="absolute top-6 left-6 text-slate-500 hover:text-white flex items-center gap-1 text-sm"><ChevronLeft size={16} /> Voltar</button>
        <button onClick={() => setShowConfig((v) => !v)} className="absolute top-6 right-6 text-slate-500 hover:text-emerald-500"><Settings size={20} /></button>

        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">{accessMode === 'viewer' ? 'Login visitante' : 'Login administrador'}</h1>
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

function Dashboard({ token, role, serverIP, prefs, onSavePrefs, onSaveServer, onLogout }) {
  const [tab, setTab] = useState('overview');
  const tabs = useMemo(() => {
    const allTabs = [
    { id: 'overview', label: 'Visao Geral', icon: LayoutDashboard },
    { id: 'birds', label: 'Aves Vistas', icon: Users },
    { id: 'devices', label: 'Dispositivos', icon: SlidersHorizontal },
    { id: 'smart', label: 'IA + IoT', icon: Activity },
    { id: 'management', label: 'Gestao', icon: Database },
    { id: 'alerts', label: 'Alertas', icon: Bell },
    { id: 'history', label: 'Historico', icon: History },
    { id: 'system', label: 'Sistema', icon: Cpu },
    { id: 'settings', label: 'Configuracoes', icon: Settings },
    ];
    if (role === 'viewer') {
      const allow = new Set(['overview', 'alerts', 'history', 'system']);
      return allTabs.filter((item) => allow.has(item.id));
    }
    return allTabs;
  }, [role]);

  const canControlDevices = role === 'admin' || role === 'operator';

  const settingsKey = `${serverIP}:${prefs.statusMs}:${prefs.historyMs}:${prefs.devicesMs}:${prefs.countMs}`;

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">
      <header className="bg-slate-900/80 border-b border-slate-800 px-6 h-20 flex justify-between items-center sticky top-0 z-30">
        <div className="flex items-center gap-3"><div className="bg-emerald-500/10 p-1 rounded-lg border border-emerald-500/20 w-11 h-11 flex items-center justify-center overflow-hidden"><img src="/logo.jpeg" alt="ChikGuard Logo" className="w-8 h-8 object-contain" /></div><h1 className="text-xl font-bold">ChickGuard AI</h1></div>
        <div className="flex items-center gap-2">
          {tabs.map((item) => {
            const Icon = item.icon;
            return <button key={item.id} onClick={() => setTab(item.id)} className={`px-3 py-2 rounded-lg text-sm border hidden md:flex items-center gap-2 ${tab === item.id ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-slate-900 border-slate-800 text-slate-400'}`}><Icon size={16} /> {item.label}</button>;
          })}
          <button onClick={onLogout} className="ml-2 flex items-center gap-2 text-slate-400 hover:text-red-400"><LogOut size={20} /><span className="hidden sm:inline">Sair</span></button>
        </div>
      </header>
      <main className="flex-1 p-6 max-w-screen-2xl mx-auto w-full">
        {tab === 'overview' && <OverviewPanel token={token} serverIP={serverIP} prefs={prefs} canControlDevices={canControlDevices} />}
        {tab === 'birds' && <BirdsPanel token={token} serverIP={serverIP} prefs={prefs} />}
        {tab === 'devices' && <DevicesPanel token={token} serverIP={serverIP} canControlDevices={canControlDevices} />}
        {tab === 'smart' && <SmartOpsPanel serverIP={serverIP} prefs={prefs} token={token} />}
        {tab === 'management' && <ManagementPanel serverIP={serverIP} prefs={prefs} />}
        {tab === 'alerts' && <AlertsPanel serverIP={serverIP} prefs={prefs} />}
        {tab === 'history' && <HistoryPanel serverIP={serverIP} prefs={prefs} />}
        {tab === 'system' && <SystemPanel serverIP={serverIP} prefs={prefs} />}
        {tab === 'settings' && <SettingsPanel key={settingsKey} serverIP={serverIP} prefs={prefs} onSavePrefs={onSavePrefs} onSaveServer={onSaveServer} />}
      </main>
    </div>
  );
}

function OverviewPanel({ token, serverIP, prefs, canControlDevices }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(false);
  const [videoBlocked, setVideoBlocked] = useState(false);
  const [historico, setHistorico] = useState([]);
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [contagem, setContagem] = useState(0);
  const [showHeatmap24, setShowHeatmap24] = useState(false);
  const [carcass, setCarcass] = useState({ count: 0, audio_alert: false, items: [] });
  const [summary, setSummary] = useState(null);

  const baseUrl = getBaseUrl(serverIP);
  const videoUrl = `${baseUrl}/api/video`;
  const webrtcUrl = `${baseUrl}/api/webrtc/offer`;
  const heatmap24Url = `${baseUrl}/api/heatmap/rolling24/image?hours=24&t=${Date.now()}`;
  const [showHeatmapOverlay, setShowHeatmapOverlay] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/status`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error();
      setDados(await r.json());
      setErro(false);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/history`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('History fetch failed');
      setHistorico(await r.json());
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchDevices = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Device state fetch failed');
      setDispositivos(await r.json());
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchCount = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/chick_count`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Count fetch failed');
      const data = await r.json();
      setContagem(data.count || 0);
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  const fetchCarcassAndSummary = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([
        fetch(`${baseUrl}/api/carcass/live`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${baseUrl}/api/summary`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (c.ok) setCarcass(await c.json());
      if (s.ok) setSummary(await s.json());
    } catch {
      setErro(true);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    fetchStatus(); fetchHistory(); fetchDevices(); fetchCount(); fetchCarcassAndSummary();
    const a = setInterval(fetchStatus, prefs.statusMs);
    const b = setInterval(fetchHistory, prefs.historyMs);
    const c = setInterval(fetchDevices, prefs.devicesMs);
    const d = setInterval(fetchCount, prefs.countMs);
    const e = setInterval(fetchCarcassAndSummary, prefs.statusMs);

    // WebSocket listener
    const socket = io(baseUrl);
    socket.on('new_alert', (data) => {
      console.log('Socket event received (OverviewPanel):', data);
      fetchStatus();
      fetchCount();
      fetchCarcassAndSummary();
      // Optionally trigger history reload if needed
      fetchHistory();
    });

    return () => {
      clearInterval(a); clearInterval(b); clearInterval(c); clearInterval(d); clearInterval(e);
      socket.disconnect();
    };
  }, [fetchStatus, fetchHistory, fetchDevices, fetchCount, fetchCarcassAndSummary, prefs, baseUrl]);

  const exportToPDF = async () => {
    const el = document.getElementById('overview-panel-content');
    if (!el) return;
    const canvas = await html2canvas(el, { scale: 1.5, useCORS: true });
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('l', 'pt', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    pdf.save(`relatorio-granja-${new Date().toISOString().slice(0,10)}.pdf`);
  };

  const exportToExcel = () => {
    const wb = XLSX.utils.book_new();
    const wsHistory = XLSX.utils.json_to_sheet(historico || []);
    XLSX.utils.book_append_sheet(wb, wsHistory, "Historico");

    const wsSummary = XLSX.utils.json_to_sheet([{
      Data: new Date().toISOString(),
      TemperaturaAtual: dados?.temperatura,
      ContagemAves: contagem,
      ComfortScore: summary?.comfort_score
    }]);
    XLSX.utils.book_append_sheet(wb, wsSummary, "Resumo");

    XLSX.writeFile(wb, `relatorio-granja-${new Date().toISOString().slice(0,10)}.xlsx`);
  };

  useEffect(() => {
    if (!carcass?.audio_alert) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);
      oscillator.type = 'square';
      oscillator.frequency.setValueAtTime(880, ctx.currentTime);
      gainNode.gain.setValueAtTime(0.001, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.08, ctx.currentTime + 0.02);
      oscillator.start();
      setTimeout(() => {
        oscillator.stop();
        ctx.close();
      }, 280);
    } catch (err) {
      console.debug('Audio error', err);
    }
  }, [carcass?.audio_alert, carcass?.count]);

  const toggleDevice = async (tipo, ligar) => {
    if (!canControlDevices) return;
    await fetch(`${baseUrl}/api/${tipo}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ligar }),
    });
    fetchDevices();
  };

  return (
    <div id="overview-panel-content" className="grid gap-6 grid-cols-1 lg:grid-cols-3 relative">
      <div className="absolute -top-12 right-0 flex gap-2 z-10 hidden md:flex">
        <button onClick={exportToPDF} className="bg-slate-800 border border-slate-700 hover:bg-slate-700 text-xs px-3 py-1.5 rounded-lg flex items-center gap-1">
          PDF
        </button>
        <button onClick={exportToExcel} className="bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/40 text-xs px-3 py-1.5 rounded-lg flex items-center gap-1">
          Excel
        </button>
      </div>
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
            <button disabled={!canControlDevices} onClick={() => toggleDevice('ventilacao', !dispositivos.ventilacao)} className={`bg-slate-950 border border-slate-800 p-4 rounded-xl flex flex-col items-center gap-3 ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : ''}`}><Wind size={22} className="text-blue-400" /><span className="text-sm">Ventilacao</span></button>
            <button disabled={!canControlDevices} onClick={() => toggleDevice('aquecedor', !dispositivos.aquecedor)} className={`bg-slate-950 border border-slate-800 p-4 rounded-xl flex flex-col items-center gap-3 ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : ''}`}><Zap size={22} className="text-orange-400" /><span className="text-sm">Aquecedor</span></button>
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <div className="text-xs uppercase tracking-wider text-slate-400 mb-1">Score de Conforto</div>
          <div className="text-5xl font-black">{summary?.comfort_score ?? '--'}</div>
          <div className="w-full h-3 bg-slate-800 rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full ${Number(summary?.comfort_score || 0) >= 80 ? 'bg-emerald-500' : Number(summary?.comfort_score || 0) >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${Math.max(0, Math.min(100, Number(summary?.comfort_score || 0)))}%` }}
            />
          </div>
        </div>
      </div>

      <div className="lg:col-span-2">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden min-h-[400px] relative">
          <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/50 absolute top-0 left-0 right-0 z-20">
            <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm"><Maximize size={16} className="text-slate-500" /> Transmissao da camera</h3>
            <div className="flex items-center gap-2">
              <button onClick={() => setShowHeatmapOverlay((v) => !v)} className="text-xs bg-slate-800 border border-slate-700 hover:bg-slate-700 rounded px-2 py-1 transition-colors">
                {showHeatmapOverlay ? 'Ocultar Heatmap Visual' : 'Mostrar Heatmap Visual'}
              </button>
              <button onClick={() => setShowHeatmap24((v) => !v)} className="text-xs bg-slate-800 border border-slate-700 hover:bg-slate-700 rounded px-2 py-1 transition-colors">
                {showHeatmap24 ? 'Mostrar Video' : 'Heatmap 24h'}
              </button>
            </div>
          </div>
          <div className="relative flex-1 bg-black flex items-center justify-center h-[500px] overflow-hidden">
            {erro ? (
              <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-900/50"><WifiOff size={32} className="text-slate-500 mb-3" /><p className="text-slate-400">Sem video</p></div>
            ) : videoBlocked ? (
              <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-900/90 p-8"><AlertTriangle size={48} className="text-yellow-500 mb-4" /><h2 className="text-xl font-bold text-white mb-2">Bloqueio do Tunnel</h2><a href={videoUrl} target="_blank" rel="noreferrer" className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-4 rounded-xl flex items-center gap-2"><ExternalLink size={18} /> Abrir stream</a></div>
            ) : showHeatmap24 ? (
              <img src={heatmap24Url} alt="Heatmap 24h" className="w-full h-full object-contain" />
            ) : (
              <>
                <WebRTCVideo url={webrtcUrl} className="w-full h-full object-contain relative z-0" onConnectionStateChange={(state) => { if(state === 'failed' && (isTunnelHost(window.location.hostname) || isTunnelHost(serverIP))) setVideoBlocked(true); }} />
                {showHeatmapOverlay && <HeatmapOverlay serverIP={serverIP} />}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function HeatmapOverlay({ serverIP }) {
  const [points, setPoints] = useState([]);
  const baseUrl = getBaseUrl(serverIP);

  const fetchHeatmapData = useCallback(async () => {
    try {
      const response = await fetch(`${baseUrl}/api/heatmap/3d?hours=2&grid=32`);
      if (response.ok) {
        const data = await response.json();
        setPoints(data.points || []);
      }
    } catch (err) {
      console.error('Heatmap fetch error:', err);
    }
  }, [baseUrl]);

  useEffect(() => {
    const bootstrap = setTimeout(fetchHeatmapData, 0);
    const interval = setInterval(fetchHeatmapData, 5000);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(interval);
    };
  }, [fetchHeatmapData]);

  if (points.length === 0) return null;

  return (
    <div className="absolute inset-0 z-10 pointer-events-none" style={{ mixBlendMode: 'screen' }}>
      {points.map((pt, i) => {
        const intensity = pt.heat_intensity || 0;
        if (intensity < 0.05) return null;

        // Define color based on intensity (blue for low, red for high)
        const isHot = intensity > 0.5;
        const colorStops = isHot
          ? `rgba(255, 0, 0, ${intensity * 0.7}) 0%, rgba(255, 0, 0, 0) 70%`
          : `rgba(0, 100, 255, ${intensity * 0.7}) 0%, rgba(0, 100, 255, 0) 70%`;

        const size = 15 + (intensity * 25);

        return (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              left: `${pt.x * 100}%`,
              top: `${pt.y * 100}%`,
              width: `${size}%`,
              height: `${size}%`,
              transform: 'translate(-50%, -50%)',
              background: `radial-gradient(circle, ${colorStops})`,
              filter: 'blur(8px)',
            }}
          />
        );
      })}
    </div>
  );
}

function DevicesPanel({ token, serverIP, canControlDevices }) {
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [autoMode, setAutoMode] = useState({ enabled: false, effective_targets: null });
  const [lightPct, setLightPct] = useState(0);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const loadDevices = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error('Device state fetch failed');
      setDispositivos(await r.json());
      const auto = await fetch(`${baseUrl}/api/auto-mode`, { headers: { Authorization: `Bearer ${token}` } });
      if (auto.ok) setAutoMode(await auto.json());
      const l = await fetch(`${baseUrl}/api/luz-dimmer`, { headers: { Authorization: `Bearer ${token}` } });
      if (l.ok) {
        const j = await l.json();
        setLightPct(Number(j.luz_intensidade_pct || 0));
      }
    } finally {
      setLoading(false);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  const toggleDevice = async (tipo, ligar) => {
    if (!canControlDevices) return;
    await fetch(`${baseUrl}/api/${tipo}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ligar }),
    });
    loadDevices();
  };

  const toggleAuto = async (enabled) => {
    if (!canControlDevices) return;
    await fetch(`${baseUrl}/api/auto-mode`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
    loadDevices();
  };

  const setDimmer = async (value) => {
    if (!canControlDevices) return;
    setLightPct(value);
    await fetch(`${baseUrl}/api/luz-dimmer`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ intensidade_pct: Number(value) }),
    });
  };

  if (loading) {
    return <div className="text-slate-400">Carregando dispositivos...</div>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <button disabled={!canControlDevices} onClick={() => toggleAuto(!autoMode.enabled)} className={`rounded-2xl border p-6 text-left ${autoMode.enabled ? 'bg-emerald-600/20 border-emerald-500/40' : 'bg-slate-900 border-slate-800'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : ''}`}>
        <div className="flex items-center justify-between mb-3"><Cpu className={autoMode.enabled ? 'text-emerald-300' : 'text-emerald-400'} /><span className={`text-xs font-bold ${autoMode.enabled ? 'text-emerald-300' : 'text-slate-500'}`}>{autoMode.enabled ? 'PILOTO AUTOMATICO' : 'MANUAL'}</span></div>
        <h3 className="font-bold text-lg">Termostato inteligente</h3>
        <p className="text-slate-400 text-sm mt-1">Liga ventilacao/aquecedor com histerese.</p>
        {autoMode.effective_targets && <p className="text-xs text-slate-400 mt-2">Fan on: {autoMode.effective_targets.fan_on_temp} C | Heater on: {autoMode.effective_targets.heater_on_temp} C</p>}
      </button>
      <button disabled={!canControlDevices} onClick={() => toggleDevice('ventilacao', !dispositivos.ventilacao)} className={`rounded-2xl border p-6 text-left ${dispositivos.ventilacao ? 'bg-blue-600/20 border-blue-500/40' : 'bg-slate-900 border-slate-800'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : ''}`}>
        <div className="flex items-center justify-between mb-3"><Wind className={dispositivos.ventilacao ? 'text-blue-300' : 'text-blue-400'} /><span className={`text-xs font-bold ${dispositivos.ventilacao ? 'text-blue-300' : 'text-slate-500'}`}>{dispositivos.ventilacao ? 'ATIVO' : 'INATIVO'}</span></div>
        <h3 className="font-bold text-lg">Ventilacao</h3>
        <p className="text-slate-400 text-sm mt-1">Controle de fluxo de ar no galpao.</p>
      </button>
      <button disabled={!canControlDevices} onClick={() => toggleDevice('aquecedor', !dispositivos.aquecedor)} className={`rounded-2xl border p-6 text-left ${dispositivos.aquecedor ? 'bg-orange-600/20 border-orange-500/40' : 'bg-slate-900 border-slate-800'} ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : ''}`}>
        <div className="flex items-center justify-between mb-3"><Zap className={dispositivos.aquecedor ? 'text-orange-300' : 'text-orange-400'} /><span className={`text-xs font-bold ${dispositivos.aquecedor ? 'text-orange-300' : 'text-slate-500'}`}>{dispositivos.aquecedor ? 'ATIVO' : 'INATIVO'}</span></div>
        <h3 className="font-bold text-lg">Aquecedor</h3>
        <p className="text-slate-400 text-sm mt-1">Estabilizacao termica automatizada.</p>
      </button>
      <div className="rounded-2xl border p-6 text-left bg-slate-900 border-slate-800 md:col-span-2">
        <div className="flex items-center justify-between mb-3"><span className="text-lg font-bold">Dimmer de Luz</span><span className="text-sm text-slate-400">{lightPct}%</span></div>
        <input disabled={!canControlDevices} type="range" min="0" max="100" value={lightPct} onChange={(e) => setLightPct(Number(e.target.value))} onMouseUp={(e) => setDimmer(Number(e.currentTarget.value))} onTouchEnd={(e) => setDimmer(Number(e.currentTarget.value))} className={`w-full ${!canControlDevices ? 'opacity-50 cursor-not-allowed' : ''}`} />
        <p className="text-slate-400 text-sm mt-2">Simulador de amanhecer/anoitecer por intensidade gradual.</p>
      </div>
    </div>
  );
}

function AlertsPanel({ serverIP, prefs }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const loadAlerts = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/alerts`);
      if (!r.ok) throw new Error('Alerts fetch failed');
      setAlerts(await r.json());
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    loadAlerts();
    const timer = setInterval(loadAlerts, prefs.statusMs);

    // WebSocket listener for instant alert updates
    const socket = io(baseUrl);
    socket.on('new_alert', (data) => {
      console.log('Socket event received (AlertsPanel):', data);
      loadAlerts();
    });

    return () => {
      clearInterval(timer);
      socket.disconnect();
    };
  }, [loadAlerts, prefs.statusMs, baseUrl]);

  if (loading) {
    return <div className="text-slate-400">Carregando alertas...</div>;
  }

  return (
    <div className="space-y-3">
      {alerts.length === 0 && <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-slate-400">Sem alertas ativos no momento.</div>}
      {alerts.map((alert) => (
        <div key={alert.id} className={`rounded-xl border p-4 ${alert.nivel === 'alto' ? 'bg-red-500/10 border-red-500/30' : alert.nivel === 'medio' ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-slate-900 border-slate-800'}`}>
          <div className="flex items-center justify-between">
            <div className="font-semibold">{alert.tipo}</div>
            <div className="text-xs text-slate-400">{alert.data} {alert.hora}</div>
          </div>
          <p className="text-sm text-slate-300 mt-2">{alert.mensagem}</p>
          {alert.temperatura !== null && <p className="text-xs text-slate-400 mt-2">Temperatura: {alert.temperatura} C</p>}
        </div>
      ))}
    </div>
  );
}

function HistoryPanel({ serverIP, prefs }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const loadHistory = useCallback(async () => {
    try {
      const r = await fetch(`${baseUrl}/api/history`);
      if (!r.ok) throw new Error('History fetch failed');
      setHistory(await r.json());
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    loadHistory();
    const timer = setInterval(loadHistory, prefs.historyMs);
    return () => clearInterval(timer);
  }, [loadHistory, prefs.historyMs]);

  if (loading) {
    return <div className="text-slate-400">Carregando historico...</div>;
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="p-3 border-b border-slate-800 flex justify-end">
        <a href={`${baseUrl}/api/reports/weekly/download`} className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3 py-2 rounded-lg">Exportar PDF semanal</a>
      </div>
      <div className="grid grid-cols-4 gap-2 px-4 py-3 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
        <span>Data</span><span>Hora</span><span>Status</span><span>Temp</span>
      </div>
      <div className="max-h-[520px] overflow-auto">
        {history.length === 0 && <div className="p-4 text-slate-500">Sem leituras registradas.</div>}
        {history.map((item) => (
          <div key={item.id} className="grid grid-cols-4 gap-2 px-4 py-3 border-b border-slate-800/70 text-sm">
            <span>{item.data}</span>
            <span className="text-slate-400">{item.hora}</span>
            <span className={item.status === 'NORMAL' ? 'text-emerald-400' : 'text-red-400'}>{item.status}</span>
            <span>{item.temp} C</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BirdsPanel({ token, serverIP, prefs }) {
  const [live, setLive] = useState({ count: 0, items: [] });
  const [registry, setRegistry] = useState({ count: 0, items: [] });
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const baseUrl = getBaseUrl(serverIP);

  const loadBirds = useCallback(async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [liveRes, regRes, historyRes] = await Promise.all([
        fetch(`${baseUrl}/api/birds/live`, { headers }),
        fetch(`${baseUrl}/api/birds/registry?limit=500`, { headers }),
        fetch(`${baseUrl}/api/birds/history?limit=300`, { headers }),
      ]);
      if (liveRes.ok) setLive(await liveRes.json());
      if (regRes.ok) setRegistry(await regRes.json());
      if (historyRes.ok) setHistory(await historyRes.json());
    } finally {
      setLoading(false);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    loadBirds();
    const timer = setInterval(loadBirds, prefs.countMs);
    return () => clearInterval(timer);
  }, [loadBirds, prefs.countMs]);

  if (loading) {
    return <div className="text-slate-400">Carregando aves vistas...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SystemCard label="Aves visiveis agora" value={live.count ?? 0} />
        <SystemCard label="Aves unicas vistas" value={registry.count ?? 0} />
        <SystemCard label="Snapshots salvos" value={history.length} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">Aves vivas no quadro</div>
          <div className="max-h-[420px] overflow-auto">
            {live.items?.length === 0 && <div className="p-4 text-slate-500">Nenhuma ave visivel no momento.</div>}
            {live.items?.map((item) => (
              <div key={item.bird_uid} className="grid grid-cols-3 gap-2 px-4 py-3 border-b border-slate-800/70 text-sm">
                <span>ID {item.bird_uid}</span>
                <span className="text-slate-400">Conf: {item.confidence}</span>
                <span className="text-slate-400">{item.last_seen_seconds}s</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">Registro persistente de aves vistas</div>
          <div className="max-h-[420px] overflow-auto">
            {registry.items?.length === 0 && <div className="p-4 text-slate-500">Sem aves registradas ainda.</div>}
            {registry.items?.map((item) => (
              <div key={item.bird_uid} className="grid grid-cols-4 gap-2 px-4 py-3 border-b border-slate-800/70 text-sm">
                <span>ID {item.bird_uid}</span>
                <span className="text-slate-400">Vezes: {item.sightings}</span>
                <span className="text-slate-400">Conf max: {item.max_confidence}</span>
                <span className="text-slate-400">{item.last_seen}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SmartOpsPanel({ serverIP, prefs, token }) {
  const baseUrl = getBaseUrl(serverIP);
  const [behavior, setBehavior] = useState(null);
  const [immobility, setImmobility] = useState({ count: 0, items: [] });
  const [sensors, setSensors] = useState(null);
  const [autoMode, setAutoMode] = useState(null);
  const [batches, setBatches] = useState({ count: 0, items: [] });
  const [cameras, setCameras] = useState({ active_camera_id: '', items: [] });
  const [reportMsg, setReportMsg] = useState('');
  const [batchForm, setBatchForm] = useState({ name: '', start_date: '' });
  const [logbook, setLogbook] = useState({ count: 0, items: [] });
  const [logNote, setLogNote] = useState('');

  const heatmapUrl = `${baseUrl}/api/heatmap/daily/image`;

  const loadData = useCallback(async () => {
    const [b, i, s, a, bt, c, lb] = await Promise.all([
      fetch(`${baseUrl}/api/behavior/live`),
      fetch(`${baseUrl}/api/immobility/live`),
      fetch(`${baseUrl}/api/sensors/live`),
      fetch(`${baseUrl}/api/auto-mode`),
      fetch(`${baseUrl}/api/batches`),
      fetch(`${baseUrl}/api/cameras`),
      fetch(`${baseUrl}/api/logbook?limit=30`),
    ]);
    if (b.ok) setBehavior(await b.json());
    if (i.ok) setImmobility(await i.json());
    if (s.ok) setSensors(await s.json());
    if (a.ok) setAutoMode(await a.json());
    if (bt.ok) setBatches(await bt.json());
    if (c.ok) setCameras(await c.json());
    if (lb.ok) setLogbook(await lb.json());
  }, [baseUrl]);

  useEffect(() => {
    const bootstrap = setTimeout(loadData, 0);
    const timer = setInterval(loadData, prefs.statusMs);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
    };
  }, [loadData, prefs.statusMs]);

  const toggleAuto = async () => {
    await fetch(`${baseUrl}/api/auto-mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ enabled: !autoMode?.enabled }),
    });
    loadData();
  };

  const createBatch = async () => {
    if (!batchForm.name || !batchForm.start_date) return;
    await fetch(`${baseUrl}/api/batches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...batchForm, active: true }),
    });
    setBatchForm({ name: '', start_date: '' });
    loadData();
  };

  const generateWeeklyReport = async () => {
    const r = await fetch(`${baseUrl}/api/reports/weekly`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
    const data = await r.json();
    setReportMsg(r.ok ? `Relatorio gerado: ${data.file}` : (data.msg || 'Falha ao gerar relatorio'));
  };

  const saveLogNote = async () => {
    if (!logNote.trim()) return;
    await fetch(`${baseUrl}/api/logbook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: logNote, author: 'tratador' }),
    });
    setLogNote('');
    loadData();
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SystemCard label="Comportamento" value={behavior?.status || '--'} />
        <SystemCard label="Imobilidade monitorada" value={immobility?.count ?? '--'} />
        <SystemCard label="Modo automatico" value={autoMode?.enabled ? 'Ativo' : 'Inativo'} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="font-bold mb-3">Sensores IoT</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-3">Temp: {sensors?.temperature_c ?? '--'} C</div>
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-3">Umidade: {sensors?.humidity_pct ?? '--'} %</div>
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-3">Amonia: {sensors?.ammonia_ppm ?? '--'} ppm</div>
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-3">Racao: {sensors?.feed_level_pct ?? '--'} %</div>
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-3">Agua: {sensors?.water_level_pct ?? '--'} %</div>
            <button onClick={toggleAuto} className="bg-emerald-600 hover:bg-emerald-500 rounded-xl p-3 font-semibold">{autoMode?.enabled ? 'Desativar Auto' : 'Ativar Auto'}</button>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="font-bold mb-3">Heatmap diario</h3>
          <img src={heatmapUrl} alt="Heatmap diario" className="w-full h-64 object-cover rounded-xl border border-slate-800" />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="font-bold mb-3">Gestao de lotes</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            <input value={batchForm.name} onChange={(e) => setBatchForm((p) => ({ ...p, name: e.target.value }))} placeholder="Nome do lote" className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2" />
            <input type="date" value={batchForm.start_date} onChange={(e) => setBatchForm((p) => ({ ...p, start_date: e.target.value }))} className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2" />
            <button onClick={createBatch} className="bg-blue-600 hover:bg-blue-500 rounded-lg px-3 py-2 font-semibold">Criar/Ativar</button>
          </div>
          <div className="max-h-48 overflow-auto space-y-2">
            {batches.items?.map((item) => (
              <div key={item.id} className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm">
                {item.name} | inicio: {item.start_date} | {item.active ? 'ATIVO' : 'inativo'}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="font-bold mb-3">Escalabilidade e relatorios</h3>
          <div className="space-y-3 text-sm">
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Camera ativa: {cameras.active_camera_id || '--'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Cameras cadastradas: {cameras.items?.length ?? 0}</div>
            <button onClick={generateWeeklyReport} className="bg-orange-600 hover:bg-orange-500 rounded-lg px-3 py-2 font-semibold">Gerar PDF semanal</button>
            {reportMsg && <div className="text-slate-300">{reportMsg}</div>}
          </div>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <h3 className="font-bold mb-3">Diario do Lote (Logbook)</h3>
        <div className="flex gap-2 mb-3">
          <input value={logNote} onChange={(e) => setLogNote(e.target.value)} placeholder="Dia 12: Vacinacao realizada..." className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm" />
          <button onClick={saveLogNote} className="bg-emerald-600 hover:bg-emerald-500 rounded-lg px-3 py-2 text-sm font-semibold">Salvar nota</button>
        </div>
        <div className="max-h-48 overflow-auto space-y-2">
          {(logbook.items || []).map((item) => (
            <div key={item.id} className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm">
              {item.timestamp} | {item.author} | {item.note}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ManagementPanel({ serverIP, prefs }) {
  const baseUrl = getBaseUrl(serverIP);
  const [weightLive, setWeightLive] = useState(null);
  const [weightCurve, setWeightCurve] = useState([]);
  const [acoustic, setAcoustic] = useState(null);
  const [acousticModel, setAcousticModel] = useState(null);
  const [thermal, setThermal] = useState({ count: 0, sectors: [], items: [] });
  const [energy, setEnergy] = useState(null);
  const [audit, setAudit] = useState({ count: 0, items: [] });
  const [sync, setSync] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [audioMsg, setAudioMsg] = useState('');
  const [sensorHistory, setSensorHistory] = useState([]);
  const [weather, setWeather] = useState(null);

  const loadManagement = useCallback(async () => {
    const [wLive, wCurve, ac, model, th, en, au, sy, sh, wf] = await Promise.all([
      fetch(`${baseUrl}/api/weight/live`),
      fetch(`${baseUrl}/api/weight/curve?days=30`),
      fetch(`${baseUrl}/api/acoustic/live`),
      fetch(`${baseUrl}/api/acoustic/model-info`),
      fetch(`${baseUrl}/api/thermal-anomalies/live?minutes=60`),
      fetch(`${baseUrl}/api/energy/summary`),
      fetch(`${baseUrl}/api/audit/logs?limit=80`),
      fetch(`${baseUrl}/api/sync/status`),
      fetch(`${baseUrl}/api/sensors/history?limit=120`),
      fetch(`${baseUrl}/api/weather/forecast`),
    ]);
    if (wLive.ok) setWeightLive(await wLive.json());
    if (wCurve.ok) setWeightCurve((await wCurve.json()).items || []);
    if (ac.ok) setAcoustic(await ac.json());
    if (model.ok) setAcousticModel(await model.json());
    if (th.ok) setThermal(await th.json());
    if (en.ok) setEnergy(await en.json());
    if (au.ok) setAudit(await au.json());
    if (sy.ok) setSync(await sy.json());
    if (sh.ok) setSensorHistory((await sh.json()).items || []);
    if (wf.ok) setWeather(await wf.json());
  }, [baseUrl]);

  const classifyAudio = async () => {
    if (!audioFile) {
      setAudioMsg('Selecione um arquivo .wav');
      return;
    }
    const form = new FormData();
    form.append('audio', audioFile);
    try {
      const r = await fetch(`${baseUrl}/api/acoustic/classify`, { method: 'POST', body: form });
      const data = await r.json();
      if (!r.ok) {
        setAudioMsg(data.msg || 'Falha na classificação');
      } else {
        setAudioMsg(`Classificado. Cough index: ${data.result.cough_index}`);
        setAcoustic(data.result);
      }
    } catch {
      setAudioMsg('Erro de rede ao classificar áudio');
    }
  };

  useEffect(() => {
    const bootstrap = setTimeout(loadManagement, 0);
    const timer = setInterval(loadManagement, prefs.historyMs);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
    };
  }, [loadManagement, prefs.historyMs]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SystemCard label="Peso medio estimado" value={weightLive ? `${weightLive.avg_weight_g} g` : '--'} />
        <SystemCard label="Indice respiratorio" value={acoustic ? acoustic.respiratory_health_index : '--'} />
        <SystemCard label="Custo energia (mes)" value={energy ? `R$ ${energy.estimated_cost}` : '--'} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="font-bold mb-3">Curva de crescimento</h3>
          <div className="h-64">
            {weightCurve.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weightCurve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="timestamp" hide />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                  <Line type="monotone" dataKey="avg_weight_g" name="Peso estimado (g)" stroke="#10b981" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="ideal_weight_g" name="Peso ideal (g)" stroke="#f59e0b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-slate-500">Sem pontos suficientes ainda.</div>}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="font-bold mb-3">Saude respiratoria</h3>
          <div className="space-y-2 text-sm">
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Indice geral: {acoustic?.respiratory_health_index ?? '--'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Indice de tosse: {acoustic?.cough_index ?? '--'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Indice de estresse sonoro: {acoustic?.stress_audio_index ?? '--'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Modelo treinado: {acousticModel?.loaded ? 'carregado' : 'nao carregado'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
              <input type="file" accept=".wav,audio/wav" onChange={(e) => setAudioFile(e.target.files?.[0] || null)} className="text-xs text-slate-300" />
              <button onClick={classifyAudio} className="mt-2 bg-emerald-600 hover:bg-emerald-500 px-3 py-1 rounded text-xs font-semibold">Classificar tosse (modelo)</button>
              {audioMsg && <p className="text-xs text-slate-300 mt-2">{audioMsg}</p>}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="font-bold mb-3">Anomalias termicas</h3>
          <p className="text-sm text-slate-400 mb-3">Detectadas: {thermal.count || 0} | Setores: {(thermal.sectors || []).join(', ') || '--'}</p>
          <div className="max-h-56 overflow-auto space-y-2">
            {(thermal.items || []).slice(0, 20).map((item) => (
              <div key={item.id} className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm">
                UID {item.bird_uid} | {item.kind} | {item.estimated_temp_c}C ({item.sector})
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="font-bold mb-3">Financeiro e Sync</h3>
          <div className="space-y-2 text-sm">
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">KWh estimado: {energy?.total_kwh ?? '--'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Custo estimado: {energy ? `R$ ${energy.estimated_cost}` : '--'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Sugestao: {energy?.suggestion || '--'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Sync pendente: {sync?.pending ?? '--'}</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">Sync URL configurada: {sync?.cloud_sync_url_configured ? 'sim' : 'nao'}</div>
            <div className={`border rounded-lg px-3 py-2 ${weather?.preheat_recommended ? 'bg-blue-500/20 border-blue-400/40' : 'bg-slate-950 border-slate-800'}`}>Previsao: {weather?.message || '--'}</div>
          </div>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <h3 className="font-bold mb-3">Nivel de Racao (historico)</h3>
        <div className="h-52">
          {sensorHistory.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sensorHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="timestamp" hide />
                <YAxis stroke="#64748b" fontSize={10} domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                <Line type="monotone" dataKey="feed_level_pct" stroke="#38bdf8" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <div className="h-full flex items-center justify-center text-slate-500">Sem dados de racao.</div>}
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <h3 className="font-bold mb-3">Audit Trail</h3>
        <div className="max-h-72 overflow-auto space-y-2">
          {(audit.items || []).slice(0, 100).map((item) => (
            <div key={item.id} className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm">
              {item.timestamp} | {item.actor} | {item.action}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SystemPanel({ serverIP, prefs }) {
  const [info, setInfo] = useState(null);
  const [summary, setSummary] = useState(null);
  const baseUrl = getBaseUrl(serverIP);

  const loadSystem = useCallback(async () => {
    const [infoRes, summaryRes] = await Promise.all([
      fetch(`${baseUrl}/api/system-info`),
      fetch(`${baseUrl}/api/summary`),
    ]);
    if (infoRes.ok) setInfo(await infoRes.json());
    if (summaryRes.ok) setSummary(await summaryRes.json());
  }, [baseUrl]);

  useEffect(() => {
    const bootstrap = setTimeout(loadSystem, 0);
    const timer = setInterval(loadSystem, prefs.statusMs);
    return () => {
      clearTimeout(bootstrap);
      clearInterval(timer);
    };
  }, [loadSystem, prefs.statusMs]);

  const uptime = info ? `${Math.floor(info.uptime_seconds / 3600)}h ${Math.floor((info.uptime_seconds % 3600) / 60)}m` : '--';

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <SystemCard label="Thread da camera" value={info?.camera_thread_alive ? 'Ativa' : 'Inativa'} />
      <SystemCard label="YOLO" value={info?.yolo_loaded ? 'Carregado' : 'Nao carregado'} />
      <SystemCard label="Uptime" value={uptime} />
      <SystemCard label="Temp media" value={summary ? `${summary.media_temperatura} C` : '--'} />
      <SystemCard label="Aves detectadas" value={summary?.contagem_aves ?? '--'} />
      <SystemCard label="Alertas ativos" value={summary?.total_alertas ?? '--'} />
    </div>
  );
}

function SystemCard({ label, value }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-wider text-slate-400">{label}</span>
        <Database size={16} className="text-slate-500" />
      </div>
      <div className="text-2xl font-bold">{value}</div>
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
