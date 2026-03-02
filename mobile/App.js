import React, { useState, useEffect, useCallback } from 'react';
import { 
  StyleSheet, Text, View, TextInput, TouchableOpacity,
  SafeAreaView, StatusBar, ScrollView, ActivityIndicator, Alert, Linking, Image
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { WebView } from 'react-native-webview';
import { 
  Thermometer, Activity, AlertTriangle, CheckCircle, 
  Settings, Save, Zap, Wind, LayoutDashboard, History, LogOut, User, Key, Users, Bell, Cpu
} from 'lucide-react-native';

const appLogo = require('./assets/logo.png');

// --- COMPONENTES DE TELA ---

// 1. TELA DE MONITORAMENTO (HOME)
const MonitorScreen = ({ serverUrl, dados, loading, chickCount, dispositivos, controlarDispositivo, loadingAcao }) => {
  const getStatusColor = () => {
    if (!dados) return "#334155";
    if (dados.status === 'CALOR') return "#dc2626";
    if (dados.status === 'FRIO') return "#2563eb";
    return "#10b981";
  };

  const videoUrl = `${serverUrl}/api/video`;

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      {/* Card Principal */}
      <View style={[styles.mainCard, { backgroundColor: getStatusColor() }]}>
        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.cardLabel}>TEMPERATURA ATUAL</Text>
            {loading ? <ActivityIndicator color="#fff"/> : 
              <Text style={styles.tempText}>{dados?.temperatura}°C</Text>
            }
          </View>
          <View style={styles.iconBox}>
            {dados?.status === 'NORMAL' ? <CheckCircle size={32} color="#FFF"/> : <AlertTriangle size={32} color="#FFF"/>}
          </View>
        </View>
        <Text style={styles.statusTitle}>{dados?.status || "Conectando..."}</Text>
        <Text style={styles.statusMsg}>{dados?.mensagem || "Verificando sensores..."}</Text>
      </View>

      {/* Novo Card de Contagem de Aves */}
      <View style={styles.countCard}>
        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.cardLabel}>AVES DETECTADAS</Text>
            <Text style={styles.countText}>{chickCount}</Text>
          </View>
          <View style={[styles.iconBox, { backgroundColor: 'rgba(16, 185, 129, 0.2)' }]}>
            <Users size={32} color="#10b981"/>
          </View>
        </View>
        <Text style={styles.statusMsg}>Contagem em tempo real via IA.</Text>
      </View>

      {/* Vídeo */}
      <Text style={styles.sectionTitle}>Transmissão da Câmera</Text>
      <View style={styles.videoContainer}>
        <WebView 
          source={{ uri: videoUrl }} 
          style={{ flex: 1, backgroundColor: 'black' }}
          scrollEnabled={true}
          nestedScrollEnabled={true}
        />
        <View style={styles.liveBadge}><Text style={styles.liveText}>AO VIVO</Text></View>
      </View>

      {/* Ações */}
      <Text style={styles.sectionTitle}>Controlo Ambiental</Text>
      <View style={styles.actionGrid}>
        <TouchableOpacity 
          style={[styles.actionButton, dispositivos.ventilacao && styles.actionButtonActiveBlue]} 
          onPress={() => controlarDispositivo('ventilacao', !dispositivos.ventilacao)}
          disabled={loadingAcao}
        >
          <Wind size={24} color={dispositivos.ventilacao ? "#fff" : "#3b82f6"} />
          <Text style={[styles.actionLabel, dispositivos.ventilacao && {color: '#fff'}]}>Ventilação</Text>
          <Text style={[styles.actionStatus, dispositivos.ventilacao && {color: 'rgba(255,255,255,0.7)'}]}>
            {dispositivos.ventilacao ? 'LIGADO' : 'DESLIGADO'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.actionButton, dispositivos.aquecedor && styles.actionButtonActiveOrange]} 
          onPress={() => controlarDispositivo('aquecedor', !dispositivos.aquecedor)}
          disabled={loadingAcao}
        >
          <Zap size={24} color={dispositivos.aquecedor ? "#fff" : "#f97316"} />
          <Text style={[styles.actionLabel, dispositivos.aquecedor && {color: '#fff'}]}>Aquecedor</Text>
          <Text style={[styles.actionStatus, dispositivos.aquecedor && {color: 'rgba(255,255,255,0.7)'}]}>
            {dispositivos.aquecedor ? 'LIGADO' : 'DESLIGADO'}
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

// 2. TELA DE HISTÓRICO
const HistoryScreen = ({ serverUrl }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const req = await fetch(`${serverUrl}/api/history`);
        const json = await req.json();
        setHistory(json);
      } catch (e) {
        console.log(e);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [serverUrl]);

  return (
    <View style={styles.container}>
      <Text style={styles.pageTitle}>Histórico de Eventos</Text>
      {loading ? <ActivityIndicator size="large" color="#10b981" /> : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {history.map((item, index) => (
            <View key={index} style={styles.historyItem}>
              <View style={[styles.historyDot, { backgroundColor: item.status === 'NORMAL' ? '#10b981' : '#ef4444' }]} />
              <View style={{flex:1}}>
                <Text style={styles.historyTemp}>{item.temp}°C - {item.status}</Text>
                <Text style={styles.historyDate}>{item.data} às {item.hora}</Text>
              </View>
            </View>
          ))}
          {history.length === 0 && <Text style={{color:'#666', textAlign:'center'}}>Nenhum dado gravado.</Text>}
        </ScrollView>
      )}
    </View>
  );
};

// 2.05 TELA DE AVES (IDs, registro e trilha)
const BirdsScreen = ({ serverUrl }) => {
  const [live, setLive] = useState({ count: 0, items: [] });
  const [registry, setRegistry] = useState({ count: 0, items: [] });
  const [selectedBird, setSelectedBird] = useState(null);
  const [path, setPath] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadBirds = useCallback(async () => {
    try {
      const [liveReq, regReq] = await Promise.all([
        fetch(`${serverUrl}/api/birds/live`),
        fetch(`${serverUrl}/api/birds/registry?limit=500`),
      ]);
      if (liveReq.ok) setLive(await liveReq.json());
      if (regReq.ok) setRegistry(await regReq.json());
    } catch (e) {
      console.log(e);
    } finally {
      setLoading(false);
    }
  }, [serverUrl]);

  const loadPath = useCallback(async (birdUid) => {
    try {
      const req = await fetch(`${serverUrl}/api/birds/path/${birdUid}?limit=200`);
      if (!req.ok) {
        setPath([]);
        return;
      }
      const json = await req.json();
      setPath(json.items || []);
    } catch (e) {
      console.log(e);
      setPath([]);
    }
  }, [serverUrl]);

  useEffect(() => {
    loadBirds();
    const timer = setInterval(loadBirds, 2500);
    return () => clearInterval(timer);
  }, [loadBirds]);

  useEffect(() => {
    if (selectedBird !== null) {
      loadPath(selectedBird);
    }
  }, [selectedBird, loadPath]);

  if (loading) {
    return <View style={styles.container}><ActivityIndicator size="large" color="#10b981" /></View>;
  }

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.pageTitle}>Aves Vistas</Text>

      <View style={styles.metricsGrid}>
        <MetricCard label="Visiveis agora" value={live.count ?? 0} />
        <MetricCard label="Aves unicas" value={registry.count ?? 0} />
        <MetricCard label="ID selecionado" value={selectedBird ?? "--"} />
      </View>

      <Text style={styles.sectionTitle}>Aves vivas no quadro</Text>
      <View style={styles.listCard}>
        {live.items?.length === 0 && <Text style={styles.emptyText}>Nenhuma ave visivel.</Text>}
        {live.items?.map((item) => (
          <TouchableOpacity key={`live-${item.bird_uid}`} style={styles.rowItem} onPress={() => setSelectedBird(item.bird_uid)}>
            <Text style={styles.rowTitle}>ID {item.bird_uid}</Text>
            <Text style={styles.rowMeta}>Conf {item.confidence} | track {item.track_id}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Registro persistente</Text>
      <View style={styles.listCard}>
        {registry.items?.length === 0 && <Text style={styles.emptyText}>Sem aves registradas.</Text>}
        {registry.items?.map((item) => (
          <TouchableOpacity key={`reg-${item.bird_uid}`} style={styles.rowItem} onPress={() => setSelectedBird(item.bird_uid)}>
            <Text style={styles.rowTitle}>ID {item.bird_uid}</Text>
            <Text style={styles.rowMeta}>Vezes {item.sightings} | Conf max {item.max_confidence}</Text>
            <Text style={styles.rowDate}>Ultima vez: {item.last_seen}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Trilha da ave selecionada</Text>
      <View style={styles.listCard}>
        {selectedBird === null && <Text style={styles.emptyText}>Toque em uma ave para carregar a trilha.</Text>}
        {selectedBird !== null && path.length === 0 && <Text style={styles.emptyText}>Sem trilha para o ID {selectedBird}.</Text>}
        {path.slice(-20).map((point) => (
          <View key={`path-${point.id}`} style={styles.rowItem}>
            <Text style={styles.rowTitle}>({point.x}, {point.y})</Text>
            <Text style={styles.rowDate}>{point.timestamp}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
};

// 2.1 TELA DE ALERTAS
const AlertsScreen = ({ serverUrl }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const req = await fetch(`${serverUrl}/api/alerts`);
        const json = await req.json();
        setAlerts(json);
      } catch (e) {
        console.log(e);
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
    const timer = setInterval(fetchAlerts, 3000);
    return () => clearInterval(timer);
  }, [serverUrl]);

  return (
    <View style={styles.container}>
      <Text style={styles.pageTitle}>Alertas do Sistema</Text>
      {loading ? <ActivityIndicator size="large" color="#10b981" /> : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {alerts.length === 0 && <Text style={{color:'#94a3b8', textAlign:'center'}}>Sem alertas ativos.</Text>}
          {alerts.map((item, index) => (
            <View key={`${item.id}-${index}`} style={[styles.alertCard, item.nivel === 'alto' ? styles.alertHigh : item.nivel === 'medio' ? styles.alertMedium : styles.alertLow]}>
              <Text style={styles.alertType}>{item.tipo}</Text>
              <Text style={styles.alertMessage}>{item.mensagem}</Text>
              <Text style={styles.alertMeta}>{item.data} {item.hora}</Text>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
};

// 2.2 TELA DE SISTEMA
const SystemScreen = ({ serverUrl }) => {
  const [summary, setSummary] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [summaryReq, infoReq] = await Promise.all([
          fetch(`${serverUrl}/api/summary`),
          fetch(`${serverUrl}/api/system-info`)
        ]);
        if (summaryReq.ok) setSummary(await summaryReq.json());
        if (infoReq.ok) setSystemInfo(await infoReq.json());
      } catch (e) {
        console.log(e);
      }
    };
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [serverUrl]);

  const uptime = systemInfo ? `${Math.floor(systemInfo.uptime_seconds / 3600)}h ${Math.floor((systemInfo.uptime_seconds % 3600) / 60)}m` : "--";

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.pageTitle}>Sistema</Text>
      <View style={styles.metricsGrid}>
        <MetricCard label="Thread Câmera" value={systemInfo?.camera_thread_alive ? "ATIVA" : "INATIVA"} />
        <MetricCard label="Modelo IA" value={systemInfo?.yolo_loaded ? "PRONTO" : "ERRO"} />
        <MetricCard label="Uptime" value={uptime} />
        <MetricCard label="Temp Média" value={summary ? `${summary.media_temperatura}°C` : "--"} />
        <MetricCard label="Aves" value={summary?.contagem_aves ?? "--"} />
        <MetricCard label="Aves vistas" value={summary?.total_aves_vistas ?? "--"} />
        <MetricCard label="Alertas" value={summary?.total_alertas ?? "--"} />
      </View>
    </ScrollView>
  );
};

// 2.3 TELA IA + IOT
const SmartOpsScreen = ({ serverUrl }) => {
  const [behavior, setBehavior] = useState(null);
  const [immobility, setImmobility] = useState({ count: 0, items: [] });
  const [sensors, setSensors] = useState(null);
  const [autoMode, setAutoMode] = useState({ enabled: false, effective_targets: null });
  const [batches, setBatches] = useState({ count: 0, items: [] });
  const [cameras, setCameras] = useState({ active_camera_id: '-', items: [] });
  const [batchName, setBatchName] = useState('');
  const [batchStartDate, setBatchStartDate] = useState('');
  const [reportMsg, setReportMsg] = useState('');
  const [loading, setLoading] = useState(true);

  const loadSmartData = useCallback(async () => {
    try {
      const [bReq, iReq, sReq, aReq, btReq, cReq] = await Promise.all([
        fetch(`${serverUrl}/api/behavior/live`),
        fetch(`${serverUrl}/api/immobility/live`),
        fetch(`${serverUrl}/api/sensors/live`),
        fetch(`${serverUrl}/api/auto-mode`),
        fetch(`${serverUrl}/api/batches`),
        fetch(`${serverUrl}/api/cameras`)
      ]);

      if (bReq.ok) setBehavior(await bReq.json());
      if (iReq.ok) setImmobility(await iReq.json());
      if (sReq.ok) setSensors(await sReq.json());
      if (aReq.ok) setAutoMode(await aReq.json());
      if (btReq.ok) setBatches(await btReq.json());
      if (cReq.ok) setCameras(await cReq.json());
    } catch (e) {
      console.log(e);
    } finally {
      setLoading(false);
    }
  }, [serverUrl]);

  useEffect(() => {
    loadSmartData();
    const timer = setInterval(loadSmartData, 3000);
    return () => clearInterval(timer);
  }, [loadSmartData]);

  const toggleAutoMode = async () => {
    try {
      await fetch(`${serverUrl}/api/auto-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !autoMode.enabled })
      });
      loadSmartData();
    } catch (e) {
      Alert.alert('Erro', 'Falha ao atualizar modo automático.');
    }
  };

  const createBatch = async () => {
    if (!batchName || !batchStartDate) {
      Alert.alert('Atenção', 'Informe nome e data do lote (YYYY-MM-DD).');
      return;
    }
    try {
      const req = await fetch(`${serverUrl}/api/batches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: batchName, start_date: batchStartDate, active: true })
      });
      if (!req.ok) {
        const err = await req.json();
        throw new Error(err.msg || 'Falha ao criar lote');
      }
      setBatchName('');
      setBatchStartDate('');
      loadSmartData();
    } catch (e) {
      Alert.alert('Erro', e.message || 'Falha ao criar lote.');
    }
  };

  const generateReport = async () => {
    try {
      const req = await fetch(`${serverUrl}/api/reports/weekly`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const json = await req.json();
      if (!req.ok) throw new Error(json.msg || 'Falha ao gerar relatório');
      setReportMsg(json.file || 'Relatório gerado.');
    } catch (e) {
      setReportMsg(e.message || 'Erro ao gerar relatório.');
    }
  };

  if (loading) {
    return <View style={styles.container}><ActivityIndicator size="large" color="#10b981" /></View>;
  }

  const heatmapUrl = `${serverUrl}/api/heatmap/daily/image?t=${Date.now()}`;

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.pageTitle}>IA + IoT</Text>

      <View style={styles.metricsGrid}>
        <MetricCard label="Comportamento" value={behavior?.status || '--'} />
        <MetricCard label="Imobilidade" value={immobility?.count ?? 0} />
        <MetricCard label="Modo Auto" value={autoMode?.enabled ? 'ATIVO' : 'INATIVO'} />
        <MetricCard label="Câmera ativa" value={cameras?.active_camera_id || '--'} />
      </View>

      <Text style={styles.sectionTitle}>Sensores</Text>
      <View style={styles.listCard}>
        <View style={styles.rowItem}><Text style={styles.rowTitle}>Temperatura</Text><Text style={styles.rowMeta}>{sensors?.temperature_c ?? '--'} °C</Text></View>
        <View style={styles.rowItem}><Text style={styles.rowTitle}>Umidade</Text><Text style={styles.rowMeta}>{sensors?.humidity_pct ?? '--'} %</Text></View>
        <View style={styles.rowItem}><Text style={styles.rowTitle}>Amônia</Text><Text style={styles.rowMeta}>{sensors?.ammonia_ppm ?? '--'} ppm</Text></View>
        <View style={styles.rowItem}><Text style={styles.rowTitle}>Ração</Text><Text style={styles.rowMeta}>{sensors?.feed_level_pct ?? '--'} %</Text></View>
        <View style={styles.rowItem}><Text style={styles.rowTitle}>Água</Text><Text style={styles.rowMeta}>{sensors?.water_level_pct ?? '--'} %</Text></View>
      </View>

      <TouchableOpacity style={styles.btnPrimary} onPress={toggleAutoMode}>
        <Cpu color="#fff" size={20} />
        <Text style={styles.btnText}>{autoMode?.enabled ? 'Desativar Piloto Automático' : 'Ativar Piloto Automático'}</Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Heatmap Diário</Text>
      <View style={styles.heatmapCard}>
        <Image source={{ uri: heatmapUrl }} style={styles.heatmapImage} resizeMode="cover" />
      </View>

      <Text style={styles.sectionTitle}>Gestão de Lotes</Text>
      <View style={styles.listCard}>
        <TextInput
          style={styles.input}
          value={batchName}
          onChangeText={setBatchName}
          placeholder="Nome do lote (ex: Lote 45)"
          placeholderTextColor="#64748b"
        />
        <TextInput
          style={styles.input}
          value={batchStartDate}
          onChangeText={setBatchStartDate}
          placeholder="Data início (YYYY-MM-DD)"
          placeholderTextColor="#64748b"
          autoCapitalize="none"
        />
        <TouchableOpacity style={styles.btnPrimary} onPress={createBatch}>
          <Save color="#fff" size={20} />
          <Text style={styles.btnText}>Criar e Ativar Lote</Text>
        </TouchableOpacity>
        {batches.items?.slice(0, 5).map((item) => (
          <View key={`batch-${item.id}`} style={styles.rowItem}>
            <Text style={styles.rowTitle}>{item.name}</Text>
            <Text style={styles.rowMeta}>{item.start_date} | {item.active ? 'ATIVO' : 'inativo'}</Text>
          </View>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Escalabilidade e Relatórios</Text>
      <View style={styles.listCard}>
        <View style={styles.rowItem}>
          <Text style={styles.rowTitle}>Câmeras cadastradas</Text>
          <Text style={styles.rowMeta}>{cameras.items?.length ?? 0}</Text>
        </View>
        <TouchableOpacity style={styles.btnPrimary} onPress={generateReport}>
          <History color="#fff" size={20} />
          <Text style={styles.btnText}>Gerar Relatório Semanal (PDF)</Text>
        </TouchableOpacity>
        {!!reportMsg && <Text style={styles.rowMeta}>{reportMsg}</Text>}
      </View>
    </ScrollView>
  );
};

const MetricCard = ({ label, value }) => (
  <View style={styles.metricCard}>
    <Text style={styles.metricLabel}>{label}</Text>
    <Text style={styles.metricValue}>{value}</Text>
  </View>
);

// 3. TELA DE CONFIGURAÇÃO
const ConfigScreen = ({ serverUrl, setServerUrl, logout }) => {
  const [tempUrl, setTempUrl] = useState(serverUrl);

  const save = async () => {
    // Remove barra no final se tiver
    const cleanUrl = tempUrl.replace(/\/$/, "");
    await AsyncStorage.setItem('cg_server_url', cleanUrl);
    setServerUrl(cleanUrl);
    Alert.alert("Sucesso", "Endereço atualizado!");
  };

  return (
    <View style={[styles.container, {padding: 20}]}>
      <Text style={styles.pageTitle}>Ajustes do Sistema</Text>
      
      <Text style={styles.label}>Endereço do Servidor (Cloudflare Tunnel ou IP)</Text>
      <TextInput 
        style={styles.input} 
        value={tempUrl} 
        onChangeText={setTempUrl} 
        placeholder="https://exemplo.trycloudflare.com" 
        placeholderTextColor="#666"
        autoCapitalize='none'
      />
      
      <TouchableOpacity style={styles.btnPrimary} onPress={save}>
        <Save color="#fff" size={20} />
        <Text style={styles.btnText}>Salvar Endereço</Text>
      </TouchableOpacity>

      <View style={{marginTop: 40, borderTopWidth:1, borderTopColor:'#334155', paddingTop:20}}>
        <TouchableOpacity style={styles.btnLogout} onPress={logout}>
          <LogOut color="#ef4444" size={20} />
          <Text style={{color:'#ef4444', fontWeight:'bold', marginLeft:10}}>Sair da Conta</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

// --- COMPONENTE PRINCIPAL (APP) ---
export default function App() {
  const [token, setToken] = useState(null);
  const [serverUrl, setServerUrl] = useState('');
  const [activeTab, setActiveTab] = useState('monitor'); // monitor, birds, smart, alerts, history, system, config
  const [dados, setDados] = useState(null);
  const [chickCount, setChickCount] = useState(0);
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [loadingAcao, setLoadingAcao] = useState(false);

  // Login States
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [loadingLogin, setLoadingLogin] = useState(false);

  useEffect(() => {
    // Carregar dados salvos
    AsyncStorage.multiGet(['cg_token', 'cg_server_url']).then(values => {
      if(values[0][1]) setToken(values[0][1]);
      if(values[1][1]) setServerUrl(values[1][1]);
    });
  }, []);

  // Polling de dados (Só roda se estiver logado e na aba monitor)
  useEffect(() => {
    if (token && serverUrl && activeTab === 'monitor') {
      const fetchStatus = async () => {
        try {
          const res = await fetch(`${serverUrl}/api/status`);
          const json = await res.json();
          setDados(json);
        } catch (e) { console.log("Erro conexão polling"); }
      };

      const fetchChickCount = async () => {
        try {
          const res = await fetch(`${serverUrl}/api/chick_count`);
          const json = await res.json();
          if (res.ok) setChickCount(json.count);
        } catch (e) { console.log("Erro conexão contagem"); }
      };

      const fetchDeviceStatus = async () => {
        try {
          const res = await fetch(`${serverUrl}/api/estado-dispositivos`);
          const json = await res.json();
          if (res.ok) setDispositivos(json);
        } catch (e) { console.log("Erro conexão dispositivos"); }
      };

      fetchStatus();
      fetchChickCount();
      fetchDeviceStatus();

      const intervalStatus = setInterval(fetchStatus, 2000);
      const intervalCount = setInterval(fetchChickCount, 2000);
      const intervalDevices = setInterval(fetchDeviceStatus, 5000);
      return () => {
        clearInterval(intervalStatus);
        clearInterval(intervalCount);
        clearInterval(intervalDevices);
      };
    }
  }, [token, serverUrl, activeTab]);

  const handleLogin = async () => {
    if(!serverUrl) return Alert.alert("Erro", "Configure o servidor (ícone engrenagem)");
    setLoadingLogin(true);
    try {
      const req = await fetch(`${serverUrl}/api/login`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ username: user, password: pass })
      });
      const data = await req.json();
      if(req.ok) {
        await AsyncStorage.setItem('cg_token', data.access_token);
        setToken(data.access_token);
      } else {
        Alert.alert("Erro", "Login falhou");
      }
    } catch (e) { Alert.alert("Erro", "Falha de conexão com " + serverUrl); }
    finally { setLoadingLogin(false); }
  };

  const controlarDispositivo = async (tipo, ligar) => {
    setLoadingAcao(true);
    try {
      const req = await fetch(`${serverUrl}/api/${tipo}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ ligar })
      });
      if (req.ok) {
        const data = await req.json();
        setDispositivos(prev => ({ ...prev, [tipo]: data[tipo] }));
      } else {
        Alert.alert("Erro", `Falha ao controlar ${tipo}`);
      }
    } catch (e) {
      Alert.alert("Erro", "Falha de conexão com o servidor.");
    } finally {
      setLoadingAcao(false);
    }
  };

  // TELA DE LOGIN
  if (!token) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#0f172a"/>
        <ScrollView contentContainerStyle={styles.centerContainer}>
          <View style={{alignItems:'center', marginBottom:30}}>
            <View style={styles.loginLogoWrap}>
              <Image source={appLogo} style={styles.loginLogoImage} resizeMode="contain" />
            </View>
            <Text style={{fontSize:28, fontWeight:'bold', color:'white'}}>ChickGuard</Text>
            <Text style={{color:'#64748b'}}>Acesso Profissional</Text>
          </View>

          {/* Config rápida de IP no login */}
          <View style={{marginBottom:20, width:'100%'}}>
             <Text style={styles.label}>ENDEREÇO DO SERVIDOR</Text>
             <TextInput style={styles.input} value={serverUrl} onChangeText={setServerUrl} placeholder="https://exemplo.trycloudflare.com" placeholderTextColor="#64748b" autoCapitalize='none'/>
          </View>

          <View style={styles.inputContainer}>
            <User color="#64748b" size={20}/>
            <TextInput style={styles.inputField} placeholder="Usuário" placeholderTextColor="#64748b" value={user} onChangeText={setUser} autoCapitalize='none' autoCorrect={false}/>
          </View>
          <View style={styles.inputContainer}>
            <Key color="#64748b" size={20}/>
            <TextInput style={styles.inputField} placeholder="Senha" placeholderTextColor="#64748b" secureTextEntry value={pass} onChangeText={setPass} autoCapitalize='none'/>
          </View>

          <TouchableOpacity style={styles.btnPrimary} onPress={handleLogin}>
            {loadingLogin ? <ActivityIndicator color="#fff"/> : <Text style={styles.btnText}>ACEDER AO SISTEMA</Text>}
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // TELA PRINCIPAL (COM ABAS)
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a"/>
      
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerBrand}>
          <Image source={appLogo} style={styles.headerLogo} resizeMode="contain" />
          <Text style={styles.appName}>ChickGuard AI</Text>
        </View>
        <Text style={{color:'#10b981', fontSize:10, fontWeight:'bold'}}>ONLINE</Text>
      </View>

      {/* Conteúdo Dinâmico */}
      <View style={{flex:1}}>
        {activeTab === 'monitor' && 
          <MonitorScreen 
            serverUrl={serverUrl} 
            dados={dados} 
            loading={!dados}
            chickCount={chickCount}
            dispositivos={dispositivos}
            controlarDispositivo={controlarDispositivo}
            loadingAcao={loadingAcao}
          />}
        {activeTab === 'birds' && <BirdsScreen serverUrl={serverUrl} />}
        {activeTab === 'smart' && <SmartOpsScreen serverUrl={serverUrl} />}
        {activeTab === 'alerts' && <AlertsScreen serverUrl={serverUrl} />}
        {activeTab === 'history' && <HistoryScreen serverUrl={serverUrl} />}
        {activeTab === 'system' && <SystemScreen serverUrl={serverUrl} />}
        {activeTab === 'config' && <ConfigScreen serverUrl={serverUrl} setServerUrl={setServerUrl} logout={() => {setToken(null); AsyncStorage.removeItem('cg_token');}} />}
      </View>

      {/* Tab Bar (Menu Inferior) */}
      <View style={styles.tabBar}>
        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('monitor')}>
          <LayoutDashboard color={activeTab==='monitor'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='monitor'?'#10b981':'#64748b'}]}>Monitor</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('history')}>
          <History color={activeTab==='history'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='history'?'#10b981':'#64748b'}]}>Histórico</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('birds')}>
          <Users color={activeTab==='birds'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='birds'?'#10b981':'#64748b'}]}>Aves</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('smart')}>
          <Activity color={activeTab==='smart'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='smart'?'#10b981':'#64748b'}]}>IA+IoT</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('alerts')}>
          <Bell color={activeTab==='alerts'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='alerts'?'#10b981':'#64748b'}]}>Alertas</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('system')}>
          <Cpu color={activeTab==='system'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='system'?'#10b981':'#64748b'}]}>Sistema</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('config')}>
          <Settings color={activeTab==='config'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='config'?'#10b981':'#64748b'}]}>Ajustes</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

// ESTILOS
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  centerContainer: { flex:1, justifyContent:'center', alignItems:'center', padding:30 },
  header: { padding: 20, borderBottomWidth:1, borderBottomColor:'#1e293b', flexDirection:'row', justifyContent:'space-between', alignItems:'center', marginTop:30 },
  headerBrand: { flexDirection:'row', alignItems:'center' },
  headerLogo: { width: 30, height: 30, marginRight: 10, borderRadius: 6 },
  appName: { fontSize: 20, fontWeight: 'bold', color: 'white' },
  loginLogoWrap: { backgroundColor:'rgba(16,185,129,0.1)', width: 104, height: 104, borderRadius: 99, marginBottom:15, borderWidth:1, borderColor: 'rgba(16,185,129,0.2)', alignItems:'center', justifyContent:'center' },
  loginLogoImage: { width: 72, height: 72 },
  pageTitle: { fontSize: 22, fontWeight:'bold', color:'white', marginBottom:20, marginTop:10, marginLeft:20 },
  
  // Tabs
  tabBar: { flexDirection:'row', borderTopWidth:1, borderTopColor:'#1e293b', backgroundColor:'#0f172a', paddingBottom:20, paddingTop:10 },
  tabItem: { flex:1, alignItems:'center', justifyContent:'center' },
  tabLabel: { fontSize:10, marginTop:4, fontWeight:'bold' },

  // Cards
  scrollContent: { padding: 20 },
  mainCard: { padding: 24, borderRadius: 24, marginBottom: 20, elevation: 5 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardLabel: { color: 'rgba(255,255,255,0.7)', fontSize: 12, fontWeight: 'bold' },
  tempText: { fontSize: 56, fontWeight: 'bold', color: '#FFF' },
  iconBox: { backgroundColor: 'rgba(255,255,255,0.1)', padding: 12, borderRadius: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)' },
  statusTitle: { fontSize: 20, fontWeight: 'bold', color: 'white', marginTop: 10 },
  statusMsg: { color: 'rgba(255,255,255,0.9)', marginTop: 5 },
  countCard: { padding: 20, borderRadius: 24, marginBottom: 20, backgroundColor: '#1e293b' },
  countText: { fontSize: 48, fontWeight: 'bold', color: '#FFF', letterSpacing: -2 },

  // Inputs
  inputContainer: { flexDirection:'row', alignItems:'center', backgroundColor:'#1e293b', borderRadius:12, paddingHorizontal:15, marginBottom:15, borderWidth:1, borderColor:'#334155' },
  inputField: { flex:1, color:'white', padding:15 },
  inputSmall: { backgroundColor:'#1e293b', color:'#10b981', padding:10, borderRadius:8, fontSize:12, marginBottom:15, borderWidth:1, borderColor:'#334155' },
  input: { backgroundColor:'#1e293b', color:'white', padding:15, borderRadius:12, marginBottom:20, borderWidth:1, borderColor:'#334155' },
  
  // Buttons
  btnPrimary: { backgroundColor: '#10b981', width:'100%', padding:18, borderRadius:16, alignItems:'center', flexDirection:'row', justifyContent:'center', gap:10 },
  btnText: { color: 'white', fontWeight: 'bold', fontSize:16 },
  btnLogout: { flexDirection:'row', alignItems:'center', padding:15, backgroundColor:'#1e293b', borderRadius:12, justifyContent:'center' },

  // Video
  sectionTitle: { color: '#94a3b8', fontSize: 12, fontWeight: 'bold', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  videoContainer: { height: 220, backgroundColor: 'black', borderRadius: 16, overflow: 'hidden', borderWidth: 1, borderColor: '#334155', marginBottom: 20, position:'relative' },
  heatmapCard: { height: 220, backgroundColor: '#111827', borderRadius: 16, overflow: 'hidden', borderWidth: 1, borderColor: '#334155', marginBottom: 20 },
  heatmapImage: { width: '100%', height: '100%' },
  liveBadge: { position:'absolute', top:10, left:10, backgroundColor:'red', paddingHorizontal:8, paddingVertical:4, borderRadius:4 },
  liveText: { color:'white', fontSize:10, fontWeight:'bold' },

  // Tunnel Blocker
  tunnelBlockerContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#1e293b', padding: 20 },
  tunnelTitle: { color: 'white', fontSize: 18, fontWeight: 'bold', marginTop: 10, marginBottom: 5 },
  tunnelText: { color: '#94a3b8', textAlign: 'center', marginBottom: 20 },
  tunnelButton: { backgroundColor: '#2563eb', padding: 12, borderRadius: 8, width: '100%', alignItems: 'center', marginBottom: 10 },
  tunnelButtonText: { color: 'white', fontWeight: 'bold' },

  // History List
  historyItem: { flexDirection:'row', alignItems:'center', backgroundColor:'#1e293b', padding:15, borderRadius:12, marginBottom:10 },
  historyDot: { width:10, height:10, borderRadius:5, marginRight:15 },
  historyTemp: { color:'white', fontWeight:'bold', fontSize:16 },
  historyDate: { color:'#94a3b8', fontSize:12 },

  // Action Grid
  actionGrid: { flexDirection:'row', gap:15 },
  actionButton: { flex:1, backgroundColor:'#1e2b3b', padding:15, borderRadius:20, alignItems:'center', borderWidth:1, borderColor:'#334155' },
  actionButtonActiveBlue: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  actionButtonActiveOrange: { backgroundColor: '#f97316', borderColor: '#f97316' },
  actionLabel: { color:'#cbd5e1', marginTop:10, fontWeight:'bold', fontSize:12 },
  actionStatus: { color: '#94a3b8', marginTop: 5, fontSize: 10, fontWeight: 'bold' },
  label: { color:'#94a3b8', marginBottom:10, fontSize:12, fontWeight:'bold' },

  // Alerts
  alertCard: { padding: 16, borderRadius: 12, marginBottom: 10, borderWidth: 1 },
  alertHigh: { backgroundColor: 'rgba(239,68,68,0.15)', borderColor: 'rgba(239,68,68,0.4)' },
  alertMedium: { backgroundColor: 'rgba(245,158,11,0.15)', borderColor: 'rgba(245,158,11,0.4)' },
  alertLow: { backgroundColor: '#1e293b', borderColor: '#334155' },
  alertType: { color: '#fff', fontWeight: 'bold', marginBottom: 6 },
  alertMessage: { color: '#cbd5e1', marginBottom: 8 },
  alertMeta: { color: '#94a3b8', fontSize: 12 },

  // System
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  metricCard: { width: '48%', backgroundColor: '#1e293b', borderColor: '#334155', borderWidth: 1, borderRadius: 12, padding: 14 },
  metricLabel: { color: '#94a3b8', fontSize: 11, marginBottom: 6 },
  metricValue: { color: 'white', fontSize: 20, fontWeight: 'bold' },

  // Birds
  listCard: { backgroundColor: '#1e293b', borderColor: '#334155', borderWidth: 1, borderRadius: 12, overflow: 'hidden', marginBottom: 16 },
  rowItem: { padding: 12, borderBottomColor: '#334155', borderBottomWidth: 1 },
  rowTitle: { color: 'white', fontWeight: 'bold' },
  rowMeta: { color: '#94a3b8', fontSize: 12, marginTop: 2 },
  rowDate: { color: '#64748b', fontSize: 11, marginTop: 2 },
  emptyText: { color: '#94a3b8', textAlign: 'center', padding: 14 }
});

