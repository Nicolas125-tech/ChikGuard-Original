import React, { useState, useEffect, useCallback } from 'react';
import { 
  StyleSheet, Text, View, TextInput, TouchableOpacity, 
  SafeAreaView, StatusBar, ScrollView, ActivityIndicator, Alert, Dimensions 
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { WebView } from 'react-native-webview';
import { 
  Thermometer, Activity, AlertTriangle, CheckCircle, 
  Settings, Save, Zap, Wind, LayoutDashboard, History, LogOut, Lock, User, Key 
} from 'lucide-react-native';

// --- COMPONENTES DE TELA ---

// 1. TELA DE MONITORAMENTO (HOME)
const MonitorScreen = ({ serverUrl, dados, loading }) => {
  const getStatusColor = () => {
    if (!dados) return "#334155";
    if (dados.status === 'CALOR') return "#dc2626";
    if (dados.status === 'FRIO') return "#2563eb";
    return "#10b981";
  };

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

      {/* Vídeo */}
      <Text style={styles.sectionTitle}>Câmera Térmica (Ao Vivo)</Text>
      <View style={styles.videoContainer}>
        <WebView 
          source={{ uri: `${serverUrl}/api/video` }} 
          style={{ flex: 1, backgroundColor: 'transparent' }}
          scrollEnabled={false}
        />
        <View style={styles.liveBadge}><Text style={styles.liveText}>AO VIVO</Text></View>
      </View>

      {/* Ações */}
      <View style={styles.actionGrid}>
        <TouchableOpacity style={styles.actionButton}>
          <Wind size={24} color="#3b82f6" />
          <Text style={styles.actionLabel}>Ventilação</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButton}>
          <Zap size={24} color="#f97316" />
          <Text style={styles.actionLabel}>Aquecedor</Text>
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
      
      <Text style={styles.label}>Endereço do Servidor (Ngrok ou IP)</Text>
      <TextInput 
        style={styles.input} 
        value={tempUrl} 
        onChangeText={setTempUrl} 
        placeholder="https://exemplo.ngrok-free.app" 
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
  const [activeTab, setActiveTab] = useState('monitor'); // monitor, history, config
  const [dados, setDados] = useState(null);

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
      fetchStatus();
      const interval = setInterval(fetchStatus, 2000);
      return () => clearInterval(interval);
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

  // TELA DE LOGIN
  if (!token) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#0f172a"/>
        <View style={styles.centerContainer}>
          <View style={{alignItems:'center', marginBottom:40}}>
            <View style={{backgroundColor:'rgba(16,185,129,0.1)', padding:20, borderRadius:50, marginBottom:15}}>
              <Lock size={48} color="#10b981" />
            </View>
            <Text style={{fontSize:28, fontWeight:'bold', color:'white'}}>ChickGuard</Text>
            <Text style={{color:'#64748b'}}>Acesso Granja</Text>
          </View>

          {/* Config rápida de IP no login */}
          <View style={{marginBottom:20, width:'100%'}}>
             <Text style={{color:'#64748b', fontSize:10, marginBottom:5}}>SERVIDOR (NGROK OU IP)</Text>
             <TextInput style={styles.inputSmall} value={serverUrl} onChangeText={setServerUrl} placeholder="https://..." placeholderTextColor="#444" autoCapitalize='none'/>
          </View>

          <View style={styles.inputContainer}>
            <User color="#64748b" size={20}/>
            <TextInput style={styles.inputField} placeholder="Usuário" placeholderTextColor="#64748b" value={user} onChangeText={setUser} autoCapitalize='none'/>
          </View>
          <View style={styles.inputContainer}>
            <Key color="#64748b" size={20}/>
            <TextInput style={styles.inputField} placeholder="Senha" placeholderTextColor="#64748b" secureTextEntry value={pass} onChangeText={setPass}/>
          </View>

          <TouchableOpacity style={styles.btnPrimary} onPress={handleLogin}>
            {loadingLogin ? <ActivityIndicator color="#fff"/> : <Text style={styles.btnText}>ENTRAR</Text>}
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
        <Text style={styles.appName}>ChickGuard AI</Text>
        <Text style={{color:'#10b981', fontSize:10, fontWeight:'bold'}}>ONLINE</Text>
      </View>

      {/* Conteúdo Dinâmico */}
      <View style={{flex:1}}>
        {activeTab === 'monitor' && <MonitorScreen serverUrl={serverUrl} dados={dados} loading={!dados}/>}
        {activeTab === 'history' && <HistoryScreen serverUrl={serverUrl} />}
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
  appName: { fontSize: 20, fontWeight: 'bold', color: 'white' },
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
  iconBox: { backgroundColor: 'rgba(255,255,255,0.2)', padding: 10, borderRadius: 12 },
  statusTitle: { fontSize: 20, fontWeight: 'bold', color: 'white', marginTop: 10 },
  statusMsg: { color: 'rgba(255,255,255,0.9)', marginTop: 5 },

  // Inputs
  inputContainer: { flexDirection:'row', alignItems:'center', backgroundColor:'#1e293b', borderRadius:12, paddingHorizontal:15, marginBottom:15, borderWidth:1, borderColor:'#334155' },
  inputField: { flex:1, color:'white', padding:15 },
  inputSmall: { backgroundColor:'#1e293b', color:'#10b981', padding:10, borderRadius:8, fontSize:12, marginBottom:15, borderWidth:1, borderColor:'#334155' },
  input: { backgroundColor:'#1e293b', color:'white', padding:15, borderRadius:12, marginBottom:20, borderWidth:1, borderColor:'#334155' },
  
  // Buttons
  btnPrimary: { backgroundColor: '#10b981', width:'100%', padding:15, borderRadius:12, alignItems:'center', flexDirection:'row', justifyContent:'center', gap:10 },
  btnText: { color: 'white', fontWeight: 'bold', fontSize:16 },
  btnLogout: { flexDirection:'row', alignItems:'center', padding:15, backgroundColor:'#1e293b', borderRadius:12, justifyContent:'center' },

  // Video
  sectionTitle: { color: '#e2e8f0', fontSize: 16, fontWeight: 'bold', marginBottom: 10 },
  videoContainer: { height: 220, backgroundColor: 'black', borderRadius: 16, overflow: 'hidden', borderWidth: 1, borderColor: '#334155', marginBottom: 20, position:'relative' },
  liveBadge: { position:'absolute', top:10, left:10, backgroundColor:'red', paddingHorizontal:8, paddingVertical:4, borderRadius:4 },
  liveText: { color:'white', fontSize:10, fontWeight:'bold' },

  // History List
  historyItem: { flexDirection:'row', alignItems:'center', backgroundColor:'#1e293b', padding:15, borderRadius:12, marginBottom:10 },
  historyDot: { width:10, height:10, borderRadius:5, marginRight:15 },
  historyTemp: { color:'white', fontWeight:'bold', fontSize:16 },
  historyDate: { color:'#94a3b8', fontSize:12 },

  // Action Grid
  actionGrid: { flexDirection:'row', gap:15 },
  actionButton: { flex:1, backgroundColor:'#1e293b', padding:20, borderRadius:16, alignItems:'center', borderWidth:1, borderColor:'#334155' },
  actionLabel: { color:'#cbd5e1', marginTop:10, fontWeight:'bold', fontSize:12 },
  label: { color:'#94a3b8', marginBottom:10, fontSize:12, fontWeight:'bold' }
});