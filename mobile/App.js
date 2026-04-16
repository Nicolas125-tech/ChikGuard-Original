import React, { useState, useEffect, useCallback } from 'react';
import { 
  StyleSheet, Text, View, TextInput, TouchableOpacity,
  SafeAreaView, StatusBar, ScrollView, ActivityIndicator, Alert, Linking, Image, Platform, BackHandler
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { WebView } from 'react-native-webview';
import * as LocalAuthentication from 'expo-local-authentication';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { supabase } from './supabaseClient';
import * as WebBrowser from 'expo-web-browser';
WebBrowser.maybeCompleteAuthSession();
import AdminPanel from './AdminPanel';
import { useAppStore } from './store';
import { io } from 'socket.io-client';
import { 
  Thermometer, Activity, CheckCircle, 
  Settings, Save, Zap, Wind, LayoutDashboard, History, LogOut, User, Key, Bird, Bell, Cpu, Database, AlertTriangle
} from 'lucide-react-native';

const appLogo = require('./assets/logo.png');

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

async function registerForPushNotificationsAsync() {
  let token;
  if (Platform.OS === 'android') {
    Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF231F7C',
    });
  }

  if (Device.isDevice) {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== 'granted') {
      console.log('Failed to get push token for push notification!');
      return;
    }
    const projectId = Constants?.expoConfig?.extra?.eas?.projectId || '88d7f081-ad08-425e-ba52-e1a199cb661e';
    token = (await Notifications.getExpoPushTokenAsync({
      projectId
    })).data;
  } else {
    console.log('Must use physical device for Push Notifications');
  }
  return token;
}

const normalizeServerUrl = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return '';

  // Accept full tunnel output lines and extract the first usable URL/host.
  const extracted =
    raw.match(/https?:\/\/[^\s"'<>]+/i)?.[0] ||
    raw.match(/[a-z0-9.-]+\.trycloudflare\.com(?::\d+)?(?:\/[^\s"'<>]*)?/i)?.[0] ||
    raw;

  const clean = extracted.replace(/[),.;]+$/, '').trim();
  if (!clean) return '';

  const isCloudflareQuick = /trycloudflare\.com/i.test(clean);
  const withScheme = /^https?:\/\//i.test(clean) ? clean : `${isCloudflareQuick ? 'https' : 'http'}://${clean}`;
  try {
    if (typeof URL === 'undefined') {
      throw new Error('URL parser unavailable');
    }
    const u = new URL(withScheme);
    const protocol = isCloudflareQuick ? 'https:' : u.protocol;
    return `${protocol}//${u.host}`;
  } catch {
    // Fallback parser for environments where URL constructor is missing/limited.
    const m = withScheme.match(/^(https?):\/\/([^\/?#]+)(?:[\/?#].*)?$/i);
    if (!m) return '';
    const protocol = isCloudflareQuick ? 'https' : m[1].toLowerCase();
    return `${protocol}://${m[2]}`;
  }
};

const fetchWithTimeout = async (url, options = {}, timeoutMs = 9000) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
};

// --- COMPONENTES DE TELA ---

// 1. TELA DE MONITORAMENTO (HOME)
const MonitorScreen = ({ serverUrl, dados, loading, chickCount, dispositivos, controlarDispositivo, loadingAcao, enviarComandoVoz, canControlDevices, isOffline }) => {
  const [videoError, setVideoError] = useState('');
  const getStatusColor = () => {
    if (!dados) return "#334155";
    if (dados.status === 'CALOR') return "#dc2626";
    if (dados.status === 'FRIO') return "#2563eb";
    return "#10b981";
  };

  const videoUrl = `${serverUrl}/api/video`;
  const hasValidServer = !!serverUrl;

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      {isOffline && (
        <View style={styles.offlineBanner}>
          <AlertTriangle size={20} color="#f59e0b" />
          <Text style={styles.offlineText}>Modo Offline - Lendo dados locais</Text>
        </View>
      )}
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
            <Bird size={32} color="#10b981"/>
          </View>
        </View>
        <Text style={styles.statusMsg}>Contagem em tempo real via IA.</Text>
      </View>

      {/* Vídeo */}
      <Text style={styles.sectionTitle}>Transmissão da Câmera</Text>
      <View style={styles.videoContainer}>
        {!hasValidServer ? (
          <View style={styles.tunnelBlockerContainer}>
            <AlertTriangle size={32} color="#f59e0b" />
            <Text style={styles.tunnelTitle}>Servidor nao configurado</Text>
            <Text style={styles.tunnelText}>Defina um URL valido em Ajustes.</Text>
          </View>
        ) : (
          <WebView 
            source={{ uri: videoUrl }} 
            style={{ flex: 1, backgroundColor: 'black' }}
            scrollEnabled={true}
            nestedScrollEnabled={true}
            onError={(e) => {
              const desc = e?.nativeEvent?.description || 'Falha ao carregar video';
              setVideoError(desc);
            }}
          />
        )}
        <View style={styles.liveBadge}><Text style={styles.liveText}>AO VIVO</Text></View>
      </View>
      {!!videoError && (
        <Text style={{ color: '#fca5a5', fontSize: 12, marginBottom: 12 }}>
          Video indisponivel: {videoError}. Verifique se o tunnel ainda esta ativo.
        </Text>
      )}

      {/* Ações */}
      <Text style={styles.sectionTitle}>Controlo Ambiental</Text>
      <View style={styles.actionGrid}>
        <TouchableOpacity 
          style={[styles.actionButton, dispositivos.ventilacao && styles.actionButtonActiveBlue, !canControlDevices && styles.actionButtonDisabled]} 
          onPress={() => controlarDispositivo('ventilacao', !dispositivos.ventilacao)}
          disabled={loadingAcao || !canControlDevices}
        >
          <Wind size={24} color={dispositivos.ventilacao ? "#fff" : "#3b82f6"} />
          <Text style={[styles.actionLabel, dispositivos.ventilacao && {color: '#fff'}]}>Ventilação</Text>
          <Text style={[styles.actionStatus, dispositivos.ventilacao && {color: 'rgba(255,255,255,0.7)'}]}>
            {dispositivos.ventilacao ? 'LIGADO' : 'DESLIGADO'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.actionButton, dispositivos.aquecedor && styles.actionButtonActiveOrange, !canControlDevices && styles.actionButtonDisabled]} 
          onPress={() => controlarDispositivo('aquecedor', !dispositivos.aquecedor)}
          disabled={loadingAcao || !canControlDevices}
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
  const history = useAppStore(state => state.history);
  const setHistory = useAppStore(state => state.setHistory);
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
const BirdsScreen = ({ serverUrl, enviarComandoVoz }) => {
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
      {!canControlDevices && (
        <Text style={{ color: '#94a3b8', fontSize: 12, marginTop: 8 }}>
          Perfil visitante: controles desativados.
        </Text>
      )}

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

      <Text style={styles.sectionTitle}>Comandos de Voz</Text>
      <TouchableOpacity style={styles.btnPrimary} onPress={enviarComandoVoz} disabled={!enviarComandoVoz}>
        <Activity color="#fff" size={20} />
        <Text style={styles.btnText}>Microfone: comandos rápidos</Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

// 2.1 TELA DE ALERTAS
const AlertsScreen = ({ serverUrl }) => {
  const alerts = useAppStore(state => state.alerts);
  const setAlerts = useAppStore(state => state.setAlerts);
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
  const systemInfo = useAppStore(state => state.systemInfo);
  const setSystemInfo = useAppStore(state => state.setSystemInfo);

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
const SmartOpsScreen = ({ serverUrl, token }) => {
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
  const [logbook, setLogbook] = useState({ count: 0, items: [] });
  const [logNote, setLogNote] = useState('');

  const loadSmartData = useCallback(async () => {
    try {
      const [bReq, iReq, sReq, aReq, btReq, cReq, lReq] = await Promise.all([
        fetch(`${serverUrl}/api/behavior/live`),
        fetch(`${serverUrl}/api/immobility/live`),
        fetch(`${serverUrl}/api/sensors/live`),
        fetch(`${serverUrl}/api/auto-mode`),
        fetch(`${serverUrl}/api/batches`),
        fetch(`${serverUrl}/api/cameras`),
        fetch(`${serverUrl}/api/logbook?limit=20`)
      ]);

      if (bReq.ok) setBehavior(await bReq.json());
      if (iReq.ok) setImmobility(await iReq.json());
      if (sReq.ok) setSensors(await sReq.json());
      if (aReq.ok) setAutoMode(await aReq.json());
      if (btReq.ok) setBatches(await btReq.json());
      if (cReq.ok) setCameras(await cReq.json());
      if (lReq.ok) setLogbook(await lReq.json());
    } catch (e) {
      console.log(e);
    } finally {
      setLoading(false);
    }
  }, [serverUrl]);

  useEffect(() => {
    loadSmartData();

    }, [loadSmartData]);

  const toggleAutoMode = async () => {
    try {
      await fetch(`${serverUrl}/api/auto-mode`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
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

  const saveLogbook = async () => {
    if (!logNote.trim()) return;
    try {
      await fetch(`${serverUrl}/api/logbook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: logNote, author: 'tratador-mobile' })
      });
      setLogNote('');
      loadSmartData();
    } catch (e) {
      Alert.alert('Erro', 'Falha ao salvar nota do lote.');
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
        <View style={styles.rowItem}><Text style={styles.rowTitle}>Ração</Text><Text style={[styles.rowMeta, (Number(sensors?.feed_level_pct ?? 100) < 20) && {color:'#ef4444', fontWeight:'bold'}]}>{sensors?.feed_level_pct ?? '--'} %</Text></View>
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

      <Text style={styles.sectionTitle}>Diário do Lote</Text>
      <View style={styles.listCard}>
        <TextInput
          style={styles.input}
          value={logNote}
          onChangeText={setLogNote}
          placeholder="Dia 12: vacinação realizada..."
          placeholderTextColor="#64748b"
        />
        <TouchableOpacity style={styles.btnPrimary} onPress={saveLogbook}>
          <Save color="#fff" size={20} />
          <Text style={styles.btnText}>Salvar Nota</Text>
        </TouchableOpacity>
        {(logbook.items || []).map((item) => (
          <View key={`log-${item.id}`} style={styles.rowItem}>
            <Text style={styles.rowTitle}>{item.author}</Text>
            <Text style={styles.rowMeta}>{item.note}</Text>
            <Text style={styles.rowDate}>{item.timestamp}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
};

const ManagementScreen = ({ serverUrl }) => {
  const [weightLive, setWeightLive] = useState(null);
  const [acoustic, setAcoustic] = useState(null);
  const [acousticModel, setAcousticModel] = useState(null);
  const [thermal, setThermal] = useState({ count: 0, sectors: [], items: [] });
  const [energy, setEnergy] = useState(null);
  const [audit, setAudit] = useState({ count: 0, items: [] });
  const [sync, setSync] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [w, a, m, t, e, au, s] = await Promise.all([
        fetch(`${serverUrl}/api/weight/live`),
        fetch(`${serverUrl}/api/acoustic/live`),
        fetch(`${serverUrl}/api/acoustic/model-info`),
        fetch(`${serverUrl}/api/thermal-anomalies/live?minutes=60`),
        fetch(`${serverUrl}/api/energy/summary`),
        fetch(`${serverUrl}/api/audit/logs?limit=40`),
        fetch(`${serverUrl}/api/sync/status`)
      ]);
      if (w.ok) setWeightLive(await w.json());
      if (a.ok) setAcoustic(await a.json());
      if (m.ok) setAcousticModel(await m.json());
      if (t.ok) setThermal(await t.json());
      if (e.ok) setEnergy(await e.json());
      if (au.ok) setAudit(await au.json());
      if (s.ok) setSync(await s.json());
    } catch (e) {
      console.log(e);
    } finally {
      setLoading(false);
    }
  }, [serverUrl]);

  useEffect(() => {
    load();

    }, [load]);

  if (loading) {
    return <View style={styles.container}><ActivityIndicator size="large" color="#10b981" /></View>;
  }

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.pageTitle}>Gestão</Text>
      <View style={styles.metricsGrid}>
        <MetricCard label="Peso médio" value={weightLive ? `${weightLive.avg_weight_g}g` : '--'} />
        <MetricCard label="Respiratório" value={acoustic ? acoustic.respiratory_health_index : '--'} />
        <MetricCard label="Custo mês" value={energy ? `R$ ${energy.estimated_cost}` : '--'} />
        <MetricCard label="Sync pendente" value={sync?.pending ?? '--'} />
      </View>

      <View style={styles.listCard}>
        <View style={styles.rowItem}>
          <Text style={styles.rowTitle}>Modelo de tosse treinado</Text>
          <Text style={styles.rowMeta}>{acousticModel?.loaded ? 'CARREGADO' : 'NAO CARREGADO'}</Text>
          {!!acousticModel?.last_error && <Text style={styles.rowDate}>{acousticModel.last_error}</Text>}
        </View>
      </View>

      <Text style={styles.sectionTitle}>Anomalias térmicas</Text>
      <View style={styles.listCard}>
        <Text style={styles.rowMeta}>Detectadas: {thermal.count || 0} | Setores: {(thermal.sectors || []).join(', ') || '--'}</Text>
        {(thermal.items || []).slice(0, 10).map((item) => (
          <View key={`th-${item.id}`} style={styles.rowItem}>
            <Text style={styles.rowTitle}>UID {item.bird_uid} - {item.kind}</Text>
            <Text style={styles.rowMeta}>{item.estimated_temp_c} °C em {item.sector}</Text>
          </View>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Audit Trail</Text>
      <View style={styles.listCard}>
        {(audit.items || []).slice(0, 20).map((item) => (
          <View key={`au-${item.id}`} style={styles.rowItem}>
            <Text style={styles.rowTitle}>{item.actor} - {item.action}</Text>
            <Text style={styles.rowDate}>{item.timestamp}</Text>
          </View>
        ))}
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
  const [saving, setSaving] = useState(false);

  const save = async () => {
    const normalized = normalizeServerUrl(tempUrl);
    if (!normalized) {
      Alert.alert("URL inválido", "Use um endereço válido, exemplo: https://abc.trycloudflare.com");
      return;
    }
    setSaving(true);
    try {
      await AsyncStorage.setItem('cg_server_url', normalized);
      setServerUrl(normalized);
      setTempUrl(normalized);
      Alert.alert("Sucesso", "Endereço atualizado!");
    } finally {
      setSaving(false);
    }
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
      
      <TouchableOpacity style={styles.btnPrimary} onPress={save} disabled={saving}>
        <Save color="#fff" size={20} />
        <Text style={styles.btnText}>{saving ? "Salvando..." : "Salvar Endereço"}</Text>
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
  const [role, setRole] = useState('admin');
  const [status, setStatus] = useState('ACTIVE');
  const [username, setUsername] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [activeTab, setActiveTab] = useState('monitor'); // monitor, birds, smart, management, alerts, history, system, config
  const [dados, setDados] = useState(null);
  const [chickCount, setChickCount] = useState(0);
  const [dispositivos, setDispositivos] = useState({ ventilacao: false, aquecedor: false });
  const [loadingAcao, setLoadingAcao] = useState(false);

  // Login States
  const [isSignUp, setIsSignUp] = useState(false);
  const [accessMode, setAccessMode] = useState('admin');
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [loadingLogin, setLoadingLogin] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const normalizedServerUrl = normalizeServerUrl(serverUrl);
  const isViewer = role === 'viewer';
  const canControlDevices = role === 'admin' || role === 'operator';
  const allowedTabs = isViewer
    ? new Set(['monitor', 'alerts', 'history', 'system', 'config'])
    : new Set(['monitor', 'history', 'birds', 'smart', 'management', 'alerts', 'system', 'config']);

  useEffect(() => {
    // Carregar dados salvos
    AsyncStorage.multiGet(['cg_token', 'cg_server_url', 'cg_role', 'cg_username']).then(async values => {
      const savedToken = values[0][1];
      const savedUrl = values[1][1];
      const savedRole = values[2][1] || 'admin';
      const savedUser = values[3][1] || '';

      if (savedUrl) setServerUrl(normalizeServerUrl(savedUrl) || savedUrl);
      if (savedRole) setRole(savedRole);
      if (savedUser) setUsername(savedUser);

      if (savedToken) {
        if (savedRole !== 'viewer') {
          try {
            const hasHardware = await LocalAuthentication.hasHardwareAsync();
            const isEnrolled = await LocalAuthentication.isEnrolledAsync();
            if (hasHardware && isEnrolled) {
              const result = await LocalAuthentication.authenticateAsync({
                promptMessage: 'Autentique para aceder ao sistema',
                fallbackLabel: 'Usar código',
                cancelLabel: 'Cancelar',
                disableDeviceFallback: false,
              });

              if (result.success) {
                setToken(savedToken);
              } else {
                // Remove token to force login
                AsyncStorage.removeItem('cg_token');
              }
            } else {
              setToken(savedToken);
            }
          } catch (e) {
            setToken(savedToken);
          }
        } else {
          setToken(savedToken);
        }
      }
    });
  }, []);

  useEffect(() => {
    if (isViewer && !allowedTabs.has(activeTab)) {
      setActiveTab('monitor');
    }
  }, [isViewer, allowedTabs, activeTab]);

  useEffect(() => {
    const onBackPress = () => {
      if (!token) return false; // Not logged in, let default behavior happen
      if (activeTab !== 'monitor') {
        setActiveTab('monitor');
        return true; // prevent default behavior (app exit)
      }
      return false; // already on home tab, exit app
    };
    BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => BackHandler.removeEventListener('hardwareBackPress', onBackPress);
  }, [activeTab, token]);

  useEffect(() => {
    if (accessMode === 'viewer' && !user) {
      setUser('visitante');
    }
  }, [accessMode, user]);

  // Conexão WebSocket Global
  useEffect(() => {
    if (token && normalizedServerUrl) {
      const socket = io(normalizedServerUrl);

      socket.on('telemetry_update', (data) => {
        useAppStore.getState().updateTelemetry(data);
      });

      socket.on('new_alert', (data) => {
        console.log('Mobile socket event received:', data);
        // Podemo também refazer o fetch manual aqui para sincronizar o cache se preciso
      });

      return () => socket.disconnect();
    }
  }, [token, normalizedServerUrl]);


  const handleGoogleLogin = async () => {
    setLoadingLogin(true);
    try {
      if (!supabase.supabaseUrl) throw new Error('Supabase nao configurado');
      const redirectUrl = Linking.createURL('');
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectUrl,
        }
      });
      if (error) throw error;
      // Tratar a sessao se o app for reaberto pela URL
    } catch (e) {
      Alert.alert('Erro', e.message);
    } finally {
      setLoadingLogin(false);
    }
  };

  const handleLogin = async () => {
    if (!user || !pass) return Alert.alert('Erro', 'Preencha usuário e senha.');
    setLoadingLogin(true);

    try {
      if (isSignUp) {
        // Registo no Supabase
        if (!supabase.supabaseUrl) throw new Error('Supabase nao configurado para registo.');
        const { data, error } = await supabase.auth.signUp({
          email: user,
          password: pass,
        });
        if (error) throw error;
        if (data?.user) {
           Alert.alert('Sucesso', 'Conta criada! Aguardando aprovação.');
           setIsSignUp(false);
           setPass('');
        }
        setLoadingLogin(false);
        return;
      }

      // Tentativa login Supabase se for email
      if (supabase.supabaseUrl && user.includes('@')) {
         const { data, error } = await supabase.auth.signInWithPassword({
            email: user,
            password: pass,
         });

         if (!error && data?.session) {
             const userRole = data.user.app_metadata?.role || 'VIEWER';
             const userStatus = data.user.app_metadata?.status || 'ACTIVE';
             await finishLogin(data.session.access_token, userRole, data.user.email, userStatus);
             return;
         }
      }

      // Fallback para API Flask Legacy
      const url = `${normalizedServerUrl}/api/login`;
      const response = await fetchWithTimeout(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass }),
      });

      const data = await response.json();
      if (!response.ok) {
        Alert.alert('Erro', data.msg || 'Credenciais inválidas.');
      } else {
        await finishLogin(data.access_token, data.role, data.username || user, data.status || 'ACTIVE');
      }
    } catch (error) {
      console.error(error);
      Alert.alert('Erro', 'Falha de conexão. Verifique o servidor IP ou URL.');
    } finally {
      setLoadingLogin(false);
    }
  };


  const handleLogout = async () => {
    if (supabase.supabaseUrl && supabase.auth) {
       await supabase.auth.signOut();
    }
    setToken(null);
    setRole('admin');
    setUsername('');
    setStatus('ACTIVE');
    AsyncStorage.multiRemove(['cg_token', 'cg_role', 'cg_username']);
  };

  const finishLogin = async (accessToken, userRole, userName, userStatus) => {
      setToken(accessToken);
      setRole(userRole);
      setUsername(userName);
      setStatus(userStatus || 'ACTIVE');
      setIsOffline(false);
      AsyncStorage.setItem('cg_token', accessToken);
      AsyncStorage.setItem('cg_role', userRole);
      AsyncStorage.setItem('cg_username', userName);
      AsyncStorage.setItem('cg_server_url', serverUrl);
  };

  const solicitarBiometria = async (reason) => {
    try {
      const hasHardware = await LocalAuthentication.hasHardwareAsync();
      const isEnrolled = await LocalAuthentication.isEnrolledAsync();
      if (!hasHardware || !isEnrolled) {
        Alert.alert("Segurança", "Biometria não disponível neste dispositivo.");
        return false;
      }
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: reason || 'Autentique para continuar',
        fallbackLabel: 'Usar código do dispositivo',
        disableDeviceFallback: false,
        cancelLabel: 'Cancelar'
      });
      if (!result.success) {
        Alert.alert("Acesso negado", "Falha na autenticação biométrica.");
        return false;
      }
      return true;
    } catch (e) {
      Alert.alert("Erro", "Não foi possível validar a biometria.");
      return false;
    }
  };

  const controlarDispositivo = async (tipo, ligar) => {
    if (!canControlDevices) {
      Alert.alert("Acesso restrito", "Perfil visitante nao pode controlar dispositivos.");
      return;
    }
    if (!normalizedServerUrl) {
      Alert.alert("Erro", "Servidor inválido. Ajuste o URL em Configurações.");
      return;
    }
    setLoadingAcao(true);
    try {
      const acaoCritica =
        (tipo === 'ventilacao' && ligar === false) ||
        (tipo === 'aquecedor' && ligar === false);
      if (acaoCritica) {
        const okBio = await solicitarBiometria(`Confirme para ${ligar ? 'ligar' : 'desligar'} ${tipo}`);
        if (!okBio) {
          setLoadingAcao(false);
          return;
        }
      }
      const req = await fetch(`${normalizedServerUrl}/api/${tipo}`, {
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

  const enviarComandoVoz = () => {
    if (!canControlDevices) {
      Alert.alert("Acesso restrito", "Perfil visitante nao pode enviar comandos.");
      return;
    }
    Alert.alert(
      "Comando de voz",
      "Selecione o comando reconhecido:",
      [
        { text: "Ligar ventilação", onPress: () => executarComandoVoz("ligar ventilacao") },
        { text: "Desligar ventilação", onPress: () => executarComandoVoz("desligar ventilacao") },
        { text: "Ligar aquecedor", onPress: () => executarComandoVoz("ligar aquecedor") },
        { text: "Cancelar", style: "cancel" }
      ]
    );
  };

  const executarComandoVoz = async (text) => {
    if (!normalizedServerUrl) {
      Alert.alert("Erro", "Servidor inválido. Ajuste o URL em Configurações.");
      return;
    }
    try {
      const okBio = await solicitarBiometria("Confirme comando de voz crítico");
      if (!okBio) return;
      const req = await fetch(`${normalizedServerUrl}/api/voice/command`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ text })
      });
      const json = await req.json();
      if (!req.ok) throw new Error(json.msg || 'Falha');
      setDispositivos(json.devices || dispositivos);
      Alert.alert("Sucesso", `Comando executado: ${json.action}`);
    } catch (e) {
      Alert.alert("Erro", e.message || "Falha ao enviar comando de voz.");
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
            <Text style={{color:'#64748b'}}>{accessMode === 'viewer' ? 'Acesso Visitante' : 'Acesso Profissional'}</Text>
          </View>

          {/* Config rápida de IP no login */}
          <View style={{marginBottom:20, width:'100%'}}>
             <Text style={styles.label}>ENDEREÇO DO SERVIDOR</Text>
             <TextInput style={styles.input} value={serverUrl} onChangeText={setServerUrl} placeholder="https://exemplo.trycloudflare.com" placeholderTextColor="#64748b" autoCapitalize='none'/>
          </View>


          <View style={styles.loginModeRow}>
            {!isSignUp && (
               <>
                 <TouchableOpacity onPress={() => setAccessMode('admin')} style={[styles.loginModeBtn, accessMode === 'admin' && styles.loginModeBtnActive]}>
                   <Text style={[styles.loginModeText, accessMode === 'admin' && styles.loginModeTextActive]}>Administrador</Text>
                 </TouchableOpacity>
                 <TouchableOpacity onPress={() => setAccessMode('viewer')} style={[styles.loginModeBtn, accessMode === 'viewer' && styles.loginModeBtnActiveBlue]}>
                   <Text style={[styles.loginModeText, accessMode === 'viewer' && styles.loginModeTextActiveBlue]}>Visitante</Text>
                 </TouchableOpacity>
               </>
            )}
            {isSignUp && (
                 <View style={[styles.loginModeBtn, styles.loginModeBtnActive]}>
                   <Text style={[styles.loginModeText, styles.loginModeTextActive]}>Criar Nova Conta</Text>
                 </View>
            )}
          </View>

          <View style={styles.inputContainer}>
            <User color="#64748b" size={20}/>
            <TextInput style={styles.inputField} placeholder={isSignUp ? "E-mail" : "Usuário ou E-mail"} placeholderTextColor="#64748b" value={user} onChangeText={setUser} autoCapitalize='none' autoCorrect={false}/>
          </View>
          <View style={styles.inputContainer}>
            <Key color="#64748b" size={20}/>
            <TextInput style={styles.inputField} placeholder="Senha" placeholderTextColor="#64748b" secureTextEntry value={pass} onChangeText={setPass} autoCapitalize='none'/>
          </View>

          <TouchableOpacity style={styles.btnPrimary} onPress={handleLogin}>
            {loadingLogin ? <ActivityIndicator color="#fff"/> : <Text style={styles.btnText}>{isSignUp ? 'CRIAR CONTA' : 'ACEDER AO SISTEMA'}</Text>}
          </TouchableOpacity>

          <TouchableOpacity style={{marginTop: 15}} onPress={() => setIsSignUp(!isSignUp)}>
            <Text style={{color: '#10b981', textAlign: 'center'}}>
              {isSignUp ? 'Já tem uma conta? Fazer Login' : 'Não tem conta? Criar agora'}
            </Text>
          </TouchableOpacity>

          <View style={{marginTop: 30, alignItems: 'center'}}>
            <Text style={{color: '#64748b', marginBottom: 10}}>Ou continue com</Text>
            <TouchableOpacity style={styles.btnGoogle} onPress={handleGoogleLogin}>
               <Text style={styles.btnGoogleText}>Google</Text>
            </TouchableOpacity>
          </View>

        </ScrollView>
      </SafeAreaView>
    );
  }

  if (activeTab === 'admin') {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <AdminPanel serverIP={normalizedServerUrl || serverUrl} token={token} />
      </SafeAreaView>
    );
  }

  if (status === 'PENDING') {
    return (
      <SafeAreaView style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <StatusBar barStyle="light-content" />
        <View style={{ backgroundColor: '#0f172a', padding: 24, borderRadius: 12, width: '85%', alignItems: 'center' }}>
          <AlertTriangle color="#f59e0b" size={48} style={{ marginBottom: 16 }} />
          <Text style={{ color: '#10b981', fontSize: 20, fontWeight: 'bold', marginBottom: 12 }}>Aguardando Aprovação</Text>
          <Text style={{ color: '#94a3b8', textAlign: 'center', marginBottom: 24 }}>A sua conta foi registada mas precisa ser ativada por um administrador do sistema.</Text>

          <TouchableOpacity
            style={[styles.button, { backgroundColor: '#334155', width: '100%' }]}
            onPress={() => {
              AsyncStorage.multiRemove(['cg_token', 'cg_role', 'cg_username']);
              setToken(null);
              setRole('admin');
              setStatus('ACTIVE');
            }}
          >
            <Text style={[styles.btnText, { textAlign: 'center' }]}>Voltar ao Login</Text>
          </TouchableOpacity>
        </View>
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
            serverUrl={normalizedServerUrl}
            dados={dados} 
            loading={!dados}
            chickCount={chickCount}
            dispositivos={dispositivos}
            controlarDispositivo={controlarDispositivo}
            loadingAcao={loadingAcao}
            enviarComandoVoz={enviarComandoVoz}
            canControlDevices={canControlDevices}
            isOffline={isOffline}
          />}
        {activeTab === 'birds' && allowedTabs.has('birds') && <BirdsScreen serverUrl={normalizedServerUrl} enviarComandoVoz={enviarComandoVoz} />}
        {activeTab === 'smart' && allowedTabs.has('smart') && <SmartOpsScreen serverUrl={normalizedServerUrl} token={token} />}
        {activeTab === 'management' && allowedTabs.has('management') && <ManagementScreen serverUrl={normalizedServerUrl} />}
        {activeTab === 'alerts' && allowedTabs.has('alerts') && <AlertsScreen serverUrl={normalizedServerUrl} />}
        {activeTab === 'history' && allowedTabs.has('history') && <HistoryScreen serverUrl={normalizedServerUrl} />}
        {activeTab === 'system' && allowedTabs.has('system') && <SystemScreen serverUrl={normalizedServerUrl} />}
        {activeTab === 'config' && allowedTabs.has('config') && <ConfigScreen serverUrl={serverUrl} setServerUrl={(v) => setServerUrl(normalizeServerUrl(v) || v)} logout={handleLogout} />}
      </View>

      {/* Tab Bar (Menu Inferior) */}
      <View style={styles.tabBar}>
        {allowedTabs.has('monitor') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('monitor')}>
            <LayoutDashboard color={activeTab==='monitor'?'#10b981':'#64748b'} size={24}/>
            <Text style={[styles.tabLabel, {color: activeTab==='monitor'?'#10b981':'#64748b'}]}>Monitor</Text>
          </TouchableOpacity>
        )}
        
        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('history')}>
          <History color={activeTab==='history'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='history'?'#10b981':'#64748b'}]}>Histórico</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('birds')}>
          <Bird color={activeTab==='birds'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='birds'?'#10b981':'#64748b'}]}>Aves</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('smart')}>
          <Activity color={activeTab==='smart'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='smart'?'#10b981':'#64748b'}]}>IA+IoT</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('management')}>
          <Database color={activeTab==='management'?'#10b981':'#64748b'} size={24}/>
          <Text style={[styles.tabLabel, {color: activeTab==='management'?'#10b981':'#64748b'}]}>Gestão</Text>
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
  loginModeRow: { flexDirection: 'row', gap: 10, marginBottom: 15, width: '100%' },
  loginModeBtn: { flex: 1, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: '#1e293b', alignItems: 'center', backgroundColor: '#0f172a' },
  loginModeBtnActive: { backgroundColor: 'rgba(16,185,129,0.2)', borderColor: 'rgba(16,185,129,0.4)' },
  loginModeBtnActiveBlue: { backgroundColor: 'rgba(59,130,246,0.2)', borderColor: 'rgba(59,130,246,0.4)' },
  loginModeText: { color: '#94a3b8', fontSize: 12, fontWeight: 'bold' },
  loginModeTextActive: { color: '#34d399' },
  loginModeTextActiveBlue: { color: '#93c5fd' },
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
  iconBox: { backgroundColor: 'rgba(255,255,255,0.1)', padding: 12, borderRadius: 12, borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)' },
  statusTitle: { fontSize: 20, fontWeight: 'bold', color: 'white', marginTop: 10 },
  statusMsg: { color: 'rgba(255,255,255,0.9)', marginTop: 5 },
  countCard: { padding: 20, borderRadius: 24, marginBottom: 20, backgroundColor: '#0f172a' },
  countText: { fontSize: 48, fontWeight: 'bold', color: '#FFF', letterSpacing: -2 },

  // Inputs
  inputContainer: { flexDirection:'row', alignItems:'center', backgroundColor:'#1e293b', borderRadius:12, paddingHorizontal:15, marginBottom:15, borderWidth:1, borderColor:'#334155' },
  inputField: { flex:1, color:'white', padding:15 },
  inputSmall: { backgroundColor:'#1e293b', color:'#10b981', padding:10, borderRadius:8, fontSize:12, marginBottom:15, borderWidth:1, borderColor:'#334155' },
  input: { backgroundColor:'#1e293b', color:'white', padding:15, borderRadius:12, marginBottom:20, borderWidth:1, borderColor:'#334155' },
  
  // Buttons
  btnGoogle: { backgroundColor: '#ffffff', padding: 15, borderRadius: 10, width: '100%', alignItems: 'center', borderColor: '#e2e8f0', borderWidth: 1 },
  btnGoogleText: { color: '#0f172a', fontWeight: 'bold' },
  btnPrimary: { backgroundColor: '#10b981', width:'100%', padding:18, borderRadius:16, alignItems:'center', flexDirection:'row', justifyContent:'center', gap:10 },
  btnText: { color: 'white', fontWeight: 'bold', fontSize:16 },
  btnLogout: { flexDirection:'row', alignItems:'center', padding:15, backgroundColor:'#1e293b', borderRadius:12, justifyContent:'center' },

  // Video
  sectionTitle: { color: '#94a3b8', fontSize: 12, fontWeight: 'bold', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  videoContainer: { height: 220, backgroundColor: 'black', borderRadius: 12, overflow: 'hidden', borderWidth: 1, borderColor: '#1e293b', marginBottom: 20, position:'relative' },
  heatmapCard: { height: 220, backgroundColor: '#111827', borderRadius: 12, overflow: 'hidden', borderWidth: 1, borderColor: '#1e293b', marginBottom: 20 },
  heatmapImage: { width: '100%', height: '100%' },
  liveBadge: { position:'absolute', top:10, left:10, backgroundColor:'red', paddingHorizontal:8, paddingVertical:4, borderRadius:4 },
  liveText: { color:'white', fontSize:10, fontWeight:'bold' },

  // Tunnel Blocker
  tunnelBlockerContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#0f172a', padding: 20 },
  tunnelTitle: { color: 'white', fontSize: 18, fontWeight: 'bold', marginTop: 10, marginBottom: 5 },
  tunnelText: { color: '#94a3b8', textAlign: 'center', marginBottom: 20 },
  tunnelButton: { backgroundColor: '#2563eb', padding: 12, borderRadius: 8, width: '100%', alignItems: 'center', marginBottom: 10 },
  tunnelButtonText: { color: 'white', fontWeight: 'bold' },

  // Offline
  offlineBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(245,158,11,0.2)', padding: 12, borderRadius: 12, marginBottom: 20, borderWidth: 1, borderColor: 'rgba(245,158,11,0.5)' },
  offlineText: { color: '#f59e0b', fontWeight: 'bold', marginLeft: 10 },

  // History List
  historyItem: { flexDirection:'row', alignItems:'center', backgroundColor:'#1e293b', padding:15, borderRadius:12, marginBottom:10 },
  historyDot: { width:10, height:10, borderRadius:5, marginRight:15 },
  historyTemp: { color:'white', fontWeight:'bold', fontSize:16 },
  historyDate: { color:'#94a3b8', fontSize:12 },

  // Action Grid
  actionGrid: { flexDirection:'row', gap:15 },
  actionButton: { flex:1, backgroundColor:'#1e2b3b', padding:15, borderRadius:20, alignItems:'center', borderWidth:1, borderColor:'#334155' },
  actionButtonDisabled: { opacity: 0.5 },
  actionButtonActiveBlue: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  actionButtonActiveOrange: { backgroundColor: '#f97316', borderColor: '#f97316' },
  actionLabel: { color:'#cbd5e1', marginTop:10, fontWeight:'bold', fontSize:12 },
  actionStatus: { color: '#94a3b8', marginTop: 5, fontSize: 10, fontWeight: 'bold' },
  label: { color:'#94a3b8', marginBottom:10, fontSize:12, fontWeight:'bold' },

  // Alerts
  alertCard: { padding: 16, borderRadius: 12, marginBottom: 10, borderWidth: 1 },
  alertHigh: { backgroundColor: 'rgba(239,68,68,0.15)', borderColor: 'rgba(239,68,68,0.4)' },
  alertMedium: { backgroundColor: 'rgba(245,158,11,0.15)', borderColor: 'rgba(245,158,11,0.4)' },
  alertLow: { backgroundColor: '#0f172a', borderColor: '#1e293b' },
  alertType: { color: '#fff', fontWeight: 'bold', marginBottom: 6 },
  alertMessage: { color: '#cbd5e1', marginBottom: 8 },
  alertMeta: { color: '#94a3b8', fontSize: 12 },

  // System
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  metricCard: { width: '48%', backgroundColor: '#0f172a', borderColor: '#1e293b', borderWidth: 1, borderRadius: 12, padding: 14 },
  metricLabel: { color: '#94a3b8', fontSize: 11, marginBottom: 6 },
  metricValue: { color: 'white', fontSize: 20, fontWeight: 'bold' },

  // Birds
  listCard: { backgroundColor: '#0f172a', borderColor: '#1e293b', borderWidth: 1, borderRadius: 12, overflow: 'hidden', marginBottom: 16 },
  rowItem: { padding: 12, borderBottomColor: '#334155', borderBottomWidth: 1 },
  rowTitle: { color: 'white', fontWeight: 'bold' },
  rowMeta: { color: '#94a3b8', fontSize: 12, marginTop: 2 },
  rowDate: { color: '#64748b', fontSize: 11, marginTop: 2 },
  emptyText: { color: '#94a3b8', textAlign: 'center', padding: 14 }
});




