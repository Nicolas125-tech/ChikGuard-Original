import React, { useState, useEffect, useCallback } from 'react';
import { 
  Thermometer, Activity, AlertTriangle, CheckCircle, 
  Settings, Wifi, LayoutDashboard, Zap, Wind, Save, 
  WifiOff, Maximize, LogOut, Lock, User, Key, LogIn, ExternalLink, Power, 
  ScanSearch
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Lógica Inteligente: Auto-deteta se estamos a aceder diretamente pelo Ngrok
const getBaseUrl = (ipOrUrl) => {
  if (window.location.hostname.includes('ngrok')) {
    return window.location.origin;
  }
  
  if (!ipOrUrl) return 'http://127.0.0.1:5000';
  const clean = ipOrUrl.replace(/\/$/, ""); 
  if (clean.startsWith('http://') || clean.startsWith('https://')) {
    return clean; 
  }
  return `http://${clean}:5000`; 
};

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('cg_token'));
  const [serverIP, setServerIP] = useState(localStorage.getItem('cg_ip') || '127.0.0.1');

  const handleLogout = () => {
    localStorage.removeItem('cg_token');
    setToken(null);
  };

  if (!token) {
    return <LoginScreen setToken={setToken} serverIP={serverIP} setServerIP={setServerIP} />;
  }

  return <Dashboard token={token} serverIP={serverIP} logout={handleLogout} />;
}

// ============================================================================
// TELA DE LOGIN
// ============================================================================
function LoginScreen({ setToken, serverIP, setServerIP }) {
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

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const baseUrl = getBaseUrl(serverIP);

    try {
      const response = await fetch(`${baseUrl}/api/login`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ username: user, password: pass })
      });

      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new Error("Servidor offline ou endereço inválido");
      }

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('cg_token', data.access_token);
        localStorage.setItem('cg_ip', baseUrl); 
        setToken(data.access_token);
      } else {
        setError(data.msg || 'Credenciais inválidas');
      }
    } catch (err) {
      console.error("Erro no login:", err);
      setError('Falha na conexão. Verifique o Servidor/Ngrok.');
    } finally {
      setLoading(false);
    }
  };

  const salvarConfigIP = () => {
    if (tempIP) {
      const cleanIP = tempIP.replace(/\/$/, "");
      setServerIP(cleanIP);
      localStorage.setItem('cg_ip', cleanIP);
      setShowConfig(false);
      setError(''); 
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 font-sans relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
         <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-emerald-500/20 rounded-full blur-[120px]"></div>
         <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-blue-500/20 rounded-full blur-[120px]"></div>
      </div>

      <div className="w-full max-w-md bg-slate-900/80 backdrop-blur-xl p-8 rounded-3xl border border-slate-800 shadow-2xl relative z-10">
        
        <button onClick={() => setShowConfig(!showConfig)} className="absolute top-6 right-6 text-slate-500 hover:text-emerald-500 transition">
          <Settings size={20} />
        </button>

        <div className="flex flex-col items-center mb-8">
          <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mb-4 border border-emerald-500/20 shadow-lg shadow-emerald-500/10">
            <Lock size={40} className="text-emerald-500" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">ChickGuard <span className="text-emerald-500">AI</span></h1>
          <p className="text-slate-400 text-sm mt-1">Acesso Restrito à Granja</p>
        </div>

        {showConfig && (
          <div className="mb-6 p-4 bg-slate-950/80 rounded-xl border border-slate-700 animate-in slide-in-from-top-2">
            <label className="text-xs text-slate-400 uppercase font-bold mb-2 block">Servidor (IP Local ou Ngrok)</label>
            <div className="flex gap-2">
              <input 
                value={tempIP}
                onChange={e => setTempIP(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-700 text-white p-3 rounded-lg font-mono text-xs focus:border-emerald-500 outline-none"
                placeholder="https://...ngrok-free.app"
              />
              <button onClick={salvarConfigIP} className="bg-emerald-600 hover:bg-emerald-500 text-white p-3 rounded-lg transition-colors">
                <Save size={18} />
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="relative group">
            <User className="absolute left-4 top-3.5 text-slate-500 group-focus-within:text-emerald-500 transition-colors" size={20} />
            <input type="text" placeholder="Usuário" value={user} onChange={e => setUser(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white py-3 pl-12 pr-4 rounded-xl focus:border-emerald-500 outline-none transition-all placeholder-slate-600" />
          </div>
          <div className="relative group">
            <Key className="absolute left-4 top-3.5 text-slate-500 group-focus-within:text-emerald-500 transition-colors" size={20} />
            <input type="password" placeholder="Senha" value={pass} onChange={e => setPass(e.target.value)} className="w-full bg-slate-950 border border-slate-800 text-white py-3 pl-12 pr-4 rounded-xl focus:border-emerald-500 outline-none transition-all placeholder-slate-600" />
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-xl text-sm flex items-center justify-center gap-2">
              <AlertTriangle size={16} /> {error}
            </div>
          )}

          <button disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 rounded-xl flex justify-center items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-emerald-500/20 mt-2">
            {loading ? <Activity className="animate-spin" size={20} /> : <span className="flex items-center gap-2"><LogIn size={20} /> Entrar no Sistema</span>}
          </button>
        </form>
      </div>
    </div>
  );
}

// ============================================================================
// DASHBOARD PRINCIPAL (PROTEGIDO)
// ============================================================================
function Dashboard({ token, serverIP, logout }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(false);
  const [videoBloqueadoNgrok, setVideoBloqueadoNgrok] = useState(false);
  const [loading, setLoading] = useState(true);
  const [ultimoUpdate, setUltimoUpdate] = useState(new Date());
  const [historico, setHistorico] = useState([]);
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [loadingAcao, setLoadingAcao] = useState(false);
  const [contagemPintinhos, setContagemPintinhos] = useState(0); // Novo estado para contagem

  const baseUrl = getBaseUrl(serverIP);
  const API_URL = `${baseUrl}/api/status`;
  const VIDEO_URL = `${baseUrl}/api/video`; 

  const buscarDados = useCallback(async () => {
    try {
      const response = await fetch(API_URL, {
        headers: { 
          'Authorization': `Bearer ${token}`,
          'ngrok-skip-browser-warning': 'true' 
        } 
      });

      if (!response.ok) {
        throw new Error(`Falha na resposta do servidor: HTTP ${response.status}`);
      }
      
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const data = await response.json();
        setDados(data);
        setUltimoUpdate(new Date());
        setErro(false);
      } else {
        throw new Error('Resposta não é um JSON válido. Pode ser um bloqueio do navegador ou Ngrok.');
      }
    } catch (error) {
      console.error("Erro ao buscar dados do backend:", error);
      setErro(true);
    } finally {
      setLoading(false);
    }
  }, [token, API_URL]);

  const buscarHistorico = useCallback(async () => {
    try {
      const response = await fetch(`${baseUrl}/api/history`, {
        headers: { 
          'Authorization': `Bearer ${token}`,
          'ngrok-skip-browser-warning': 'true' 
        } 
      });
      if (response.ok) {
        const data = await response.json();
        setHistorico(data);
      }
    } catch (error) {
      console.error("Erro ao buscar histórico:", error);
    }
  }, [token, baseUrl]);

  const buscarEstadoDispositivos = useCallback(async () => {
    try {
      const response = await fetch(`${baseUrl}/api/estado-dispositivos`, {
        headers: { 
          'Authorization': `Bearer ${token}`,
          'ngrok-skip-browser-warning': 'true' 
        } 
      });
      if (response.ok) {
        const data = await response.json();
        setDispositivos(data);
      }
    } catch (error) {
      console.error("Erro ao buscar estado dos dispositivos:", error);
    }
  }, [token, baseUrl]);

  const buscarContagemPintinhos = useCallback(async () => {
    try {
      const response = await fetch(`${baseUrl}/api/chick_count`, {
        headers: { 
          'Authorization': `Bearer ${token}`,
          'ngrok-skip-browser-warning': 'true' 
        } 
      });
      if (response.ok) {
        const data = await response.json();
        setContagemPintinhos(data.count);
      }
    } catch (error) {
      console.error("Erro ao buscar contagem de pintinhos:", error);
    }
  }, [token, baseUrl]);


  const controlarDispositivo = async (tipo, ligar) => {
    setLoadingAcao(true);
    try {
      const response = await fetch(`${baseUrl}/api/${tipo}`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true' 
        },
        body: JSON.stringify({ ligar })
      });
      if (response.ok) {
        const data = await response.json();
        setDispositivos(prev => ({ ...prev, [tipo]: data[tipo] }));
      }
    } catch (error) {
      console.error(`Erro ao controlar ${tipo}:`, error);
    } finally {
      setLoadingAcao(false);
    }
  };

  useEffect(() => {
    buscarDados();
    buscarHistorico();
    buscarEstadoDispositivos();
    buscarContagemPintinhos();
    
    const intervalDados = setInterval(buscarDados, 2000);
    const intervalHistorico = setInterval(buscarHistorico, 10000);
    const intervalDispositivos = setInterval(buscarEstadoDispositivos, 5000);
    const intervalContagem = setInterval(buscarContagemPintinhos, 2000); // Buscar contagem a cada 2 segundos
    
    return () => {
      clearInterval(intervalDados);
      clearInterval(intervalHistorico);
      clearInterval(intervalDispositivos);
      clearInterval(intervalContagem);
    };
  }, [buscarDados, buscarHistorico, buscarEstadoDispositivos, buscarContagemPintinhos]);

  const tentarRecarregarVideo = () => {
    setVideoBloqueadoNgrok(false);
    setTimeout(() => {
        const img = document.getElementById('camera-feed');
        if (img) img.src = `${VIDEO_URL}?t=${new Date().getTime()}`;
    }, 1000);
  };

  const getStatusColor = () => {
    if (erro || !dados) return "bg-slate-800 border-slate-700";
    if (dados.status === 'FRIO') return "bg-blue-900/40 border-blue-500";
    if (dados.status === 'CALOR') return "bg-red-900/40 border-red-500";
    return "bg-emerald-900/40 border-emerald-500";
  };

  const getTextColor = () => {
    if (erro || !dados) return "text-slate-400";
    if (dados.status === 'FRIO') return "text-blue-400";
    if (dados.status === 'CALOR') return "text-red-400";
    return "text-emerald-400";
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans flex flex-col">
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex justify-between items-center sticky top-0 z-50 shadow-md">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20">
            <Activity className="text-emerald-500" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">ChickGuard <span className="text-emerald-500">AI</span></h1>
            <p className="text-[10px] text-slate-500 font-mono hidden sm:block uppercase tracking-wider">
              {ultimoUpdate.toLocaleTimeString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold transition-colors ${erro ? 'bg-red-500/10 border-red-500/50 text-red-500' : 'bg-emerald-500/10 border-emerald-500/50 text-emerald-500'}`}>
            {erro ? <WifiOff size={14} /> : <Wifi size={14} />}
            <span className="hidden sm:inline">{erro ? "OFFLINE" : "ONLINE"}</span>
          </div>
          <div className="h-8 w-px bg-slate-800 mx-2"></div>
          <button onClick={logout} className="flex items-center gap-2 text-slate-400 hover:text-red-400 transition-colors group">
            <span className="text-sm font-medium hidden sm:block group-hover:text-red-400">Sair</span>
            <LogOut size={20} />
          </button>
        </div>
      </header>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <div className={`p-6 rounded-2xl border-2 transition-all duration-500 shadow-xl relative overflow-hidden group ${getStatusColor()}`}>
              <div className="relative z-10">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-2 text-slate-300 font-bold text-xs uppercase tracking-widest">
                    <Thermometer size={16} /> Temperatura Média
                  </div>
                  {loading && !dados ? <Activity className="animate-spin" size={20}/> : 
                   (dados?.status === "NORMAL" ? <CheckCircle className="text-emerald-500" /> : <AlertTriangle className={getTextColor()} />)
                  }
                </div>
                <div className="text-7xl font-bold text-white mb-2 tracking-tighter">
                  {dados ? dados.temperatura : '--'}°C
                </div>
                <div className={`inline-block px-3 py-1 rounded-lg font-bold text-sm bg-slate-950/40 border border-white/10 backdrop-blur-md ${getTextColor()}`}>
                  {erro ? "SEM CONEXÃO" : (dados ? dados.status : "A CARREGAR...")}
                </div>
                <p className="mt-4 text-slate-300 text-sm leading-relaxed border-l-2 border-white/10 pl-3">
                  {erro ? "Verifique se o backend Python está a rodar e se o IP/Ngrok está correto." : (dados ? dados.mensagem : "Aguardando dados...")}
                </p>
              </div>
              <div className={`absolute -right-10 -bottom-10 w-40 h-40 rounded-full blur-[80px] opacity-20 transition-colors duration-500 ${getTextColor().replace('text-', 'bg-')}`}></div>
            </div>

            {/* Novo Card para Contagem de Aves */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-2 text-slate-300 font-bold text-xs uppercase tracking-widest">
                  <ScanSearch size={16} /> Contagem de Objetos
                </div>
                {loading && contagemPintinhos === 0 ? <Activity className="animate-spin" size={20}/> : 
                  <CheckCircle className="text-emerald-500" />
                }
              </div>
              <div className="text-7xl font-bold text-white mb-2 tracking-tighter">
                {erro ? '--' : contagemPintinhos}
              </div>
              <div className={`inline-block px-3 py-1 rounded-lg font-bold text-sm bg-slate-950/40 border border-white/10 backdrop-blur-md text-emerald-400`}>
                OBJETOS DETECTADOS
              </div>
              <p className="mt-4 text-slate-300 text-sm leading-relaxed border-l-2 border-white/10 pl-3">
                Contagem em tempo real via visão computacional.
              </p>
            </div>


            {/* Gráfico de Histórico */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg">
              <h3 className="text-slate-400 text-xs font-bold uppercase mb-4 flex items-center gap-2 tracking-widest">
                <LayoutDashboard size={14} /> Histórico de Temperatura
              </h3>
              <div className="h-40">
                {historico.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={historico}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="hora" stroke="#64748b" fontSize={10} />
                      <YAxis domain={['dataMin - 2', 'dataMax + 2']} stroke="#64748b" fontSize={10} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                        labelStyle={{ color: '#fff' }}
                      />
                      <Line type="monotone" dataKey="temp" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981' }} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                    Carregando gráfico...
                  </div>
                )}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
              <h3 className="text-slate-400 text-xs font-bold uppercase mb-4 flex items-center gap-2 tracking-widest">
                <Power size={14} /> Controlo Ambiental
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <button 
                  onClick={() => controlarDispositivo('ventilacao', !dispositivos.ventilacao)}
                  disabled={loadingAcao}
                  className={`bg-slate-950 border p-4 rounded-xl flex flex-col items-center gap-3 transition-all group active:scale-95 ${dispositivos.ventilacao ? 'border-blue-500 bg-blue-500/10' : 'border-slate-800 hover:border-blue-500/50 hover:bg-blue-500/5'}`}
                >
                  <div className={`p-3 rounded-full transition-colors ${dispositivos.ventilacao ? 'bg-blue-500 text-white' : 'bg-blue-500/10 text-blue-500 group-hover:bg-blue-500/20'}`}>
                    <Wind size={24} />
                  </div>
                  <span className="text-sm font-medium text-slate-300">Ventilação</span>
                  <span className={`text-xs font-bold ${dispositivos.ventilacao ? 'text-blue-400' : 'text-slate-500'}`}>
                    {dispositivos.ventilacao ? 'LIGADO' : 'DESLIGADO'}
                  </span>
                </button>
                <button 
                  onClick={() => controlarDispositivo('aquecedor', !dispositivos.aquecedor)}
                  disabled={loadingAcao}
                  className={`bg-slate-950 border p-4 rounded-xl flex flex-col items-center gap-3 transition-all group active:scale-95 ${dispositivos.aquecedor ? 'border-orange-500 bg-orange-500/10' : 'border-slate-800 hover:border-orange-500/50 hover:bg-orange-500/5'}`}
                >
                  <div className={`p-3 rounded-full transition-colors ${dispositivos.aquecedor ? 'bg-orange-500 text-white' : 'bg-orange-500/10 text-orange-500 group-hover:bg-orange-500/20'}`}>
                    <Zap size={24} />
                  </div>
                  <span className="text-sm font-medium text-slate-300">Aquecedor</span>
                  <span className={`text-xs font-bold ${dispositivos.aquecedor ? 'text-orange-400' : 'text-slate-500'}`}>
                    {dispositivos.aquecedor ? 'LIGADO' : 'DESLIGADO'}
                  </span>
                </button>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl h-full min-h-[400px] flex flex-col relative group">
              <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/50 backdrop-blur-sm absolute top-0 left-0 right-0 z-20">
                <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm">
                  <Maximize size={16} className="text-slate-500" /> Transmissão da Câmera
                </h3>
                {!erro && !videoBloqueadoNgrok && <span className="flex items-center gap-2 text-[10px] font-bold text-red-500 animate-pulse bg-red-500/10 px-2 py-1 rounded border border-red-500/20"><span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span> AO VIVO</span>}
              </div>
              
              <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden">
                {erro ? (
                  <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-900/50">
                    <div className="bg-slate-800 p-4 rounded-full mb-4 animate-pulse">
                      <WifiOff size={32} className="text-slate-500" />
                    </div>
                    <p className="text-slate-400 font-medium">Sinal de vídeo perdido</p>
                  </div>
                ) : videoBloqueadoNgrok ? (
                   <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-900/90 p-8 z-30">
                     <AlertTriangle size={48} className="text-yellow-500 mb-4" />
                     <h2 className="text-xl font-bold text-white mb-2">Bloqueio do Ngrok Ativo</h2>
                     <p className="text-slate-400 text-sm mb-6 max-w-sm">
                       Como você está usando o Ngrok gratuito, o navegador bloqueou o vídeo por segurança.
                     </p>
                     
                     <div className="flex flex-col gap-3 w-full max-w-xs">
                        <a 
                          href={VIDEO_URL} 
                          target="_blank" 
                          rel="noreferrer"
                          className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-4 rounded-xl flex items-center justify-center gap-2 transition-colors"
                        >
                          <ExternalLink size={18} /> 1. Clique aqui e "Visit Site"
                        </a>
                        <button 
                          onClick={tentarRecarregarVideo}
                          className="bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white font-bold py-3 px-4 rounded-xl transition-colors"
                        >
                          2. Já cliquei, carregar vídeo!
                        </button>
                     </div>
                   </div>
                ) : (
                  <img 
                    id="camera-feed"
                    src={VIDEO_URL} 
                    alt="Visão da Câmera" 
                    className="w-full h-full object-contain"
                    onError={(e) => { 
                      if(window.location.hostname.includes('ngrok') || serverIP.includes('ngrok')) {
                          setVideoBloqueadoNgrok(true);
                      } else {
                          e.target.onerror = null; 
                          e.target.src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiB2aWV3Qm94PSIwIDAgNDAwIDMwMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iIzE1MTcxZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmF0LWJhc2VsaW5lPSJtaWRkbGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiMzMzQxNTUiIGZvbnQtZmFtaWx5PSJtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTQiPkFHVUFSREFORE8gU1RSRUFNLi4uPC90ZXh0Pjwvc3ZnPg==";
                      }
                    }}
                  />
                )}
                
                {!erro && !videoBloqueadoNgrok && (
                  <>
                    <div className="absolute bottom-4 left-4 bg-black/60 backdrop-blur px-3 py-1.5 rounded border border-white/10 z-20">
                      <p className="text-[10px] text-emerald-500 font-mono tracking-wider">CÂMERA COM DETECÇÃO IA</p>
                    </div>
                    <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_2px,3px_100%] pointer-events-none z-10"></div>
                  </>
                )}
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
