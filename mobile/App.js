import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, Text, View, TextInput, TouchableOpacity,
  SafeAreaView, StatusBar, ScrollView, ActivityIndicator, Alert, Image, Platform, BackHandler
} from 'react-native';
import * as Linking from 'expo-linking';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as LocalAuthentication from 'expo-local-authentication';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { supabase } from './supabaseClient';
import * as WebBrowser from 'expo-web-browser';
WebBrowser.maybeCompleteAuthSession();

// Modular Screens
import MonitorScreen from './screens/MonitorScreen';
import HistoryScreen from './screens/HistoryScreen';
import BirdsScreen from './screens/BirdsScreen';
import SmartOpsScreen from './screens/SmartOpsScreen';
import ManagementScreen from './screens/ManagementScreen';
import AlertsScreen from './screens/AlertsScreen';
import SystemScreen from './screens/SystemScreen';
import ConfigScreen from './screens/ConfigScreen';
import DigitalTwinScreen from './screens/DigitalTwinScreen';
import AdminPanel from './AdminPanel';

import { 
  LayoutDashboard, History, Bird, Activity, Database, Bell, Cpu, Settings, Layers, LogOut, User, Key, AlertTriangle
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
      console.warn('Failed to get push token for push notification!');
      return;
    }
    const projectId = Constants?.expoConfig?.extra?.eas?.projectId || '88d7f081-ad08-425e-ba52-e1a199cb661e';
    token = (await Notifications.getExpoPushTokenAsync({
      projectId
    })).data;
  } else {
    console.warn('Must use physical device for Push Notifications');
  }
  return token;
}

const normalizeServerUrl = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return '';

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

export default function App() {
  const [token, setToken] = useState(null);
  const [role, setRole] = useState('admin');
  const [status, setStatus] = useState('ACTIVE');
  const [username, setUsername] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [activeTab, setActiveTab] = useState('monitor'); // monitor, digitalTwin, birds, smart, management, alerts, history, system, config
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
    ? new Set(['monitor', 'digitalTwin', 'alerts', 'history', 'system', 'config'])
    : new Set(['monitor', 'digitalTwin', 'history', 'birds', 'smart', 'management', 'alerts', 'system', 'config']);

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
      if (!token) return false;
      if (activeTab !== 'monitor') {
        setActiveTab('monitor');
        return true;
      }
      return false;
    };
    BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => BackHandler.removeEventListener('hardwareBackPress', onBackPress);
  }, [activeTab, token]);

  useEffect(() => {
    if (accessMode === 'viewer' && !user) {
      setUser('visitante');
    }
  }, [accessMode, user]);

  // Polling de dados
  useEffect(() => {
    if (token && normalizedServerUrl && activeTab === 'monitor') {
      const fetchStatus = async () => {
        try {
          const res = await fetch(`${normalizedServerUrl}/api/status`, { headers: { Authorization: `Bearer ${token}` } });
          const json = await res.json();
          setDados(json);
          setIsOffline(false);
          await AsyncStorage.setItem('offline_dados', JSON.stringify(json));
        } catch (e) {
          setIsOffline(true);
          const local = await AsyncStorage.getItem('offline_dados');
          if (local) setDados(JSON.parse(local));
        }
      };

      const fetchChickCount = async () => {
        try {
          const res = await fetch(`${normalizedServerUrl}/api/chick_count`, { headers: { Authorization: `Bearer ${token}` } });
          const json = await res.json();
          if (res.ok) {
            setChickCount(json.count);
            await AsyncStorage.setItem('offline_chickCount', JSON.stringify(json.count));
          }
        } catch (e) {
          const local = await AsyncStorage.getItem('offline_chickCount');
          if (local) setChickCount(JSON.parse(local));
        }
      };

      const fetchDeviceStatus = async () => {
        try {
          const res = await fetch(`${normalizedServerUrl}/api/estado-dispositivos`, { headers: { Authorization: `Bearer ${token}` } });
          const json = await res.json();
          if (res.ok) {
            setDispositivos(json);
            await AsyncStorage.setItem('offline_dispositivos', JSON.stringify(json));
          }
        } catch (e) {
          const local = await AsyncStorage.getItem('offline_dispositivos');
          if (local) setDispositivos(JSON.parse(local));
        }
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
  }, [token, normalizedServerUrl, activeTab]);

  const handleGoogleLogin = async () => {
    setLoadingLogin(true);
    try {
      if (!supabase.supabaseUrl) throw new Error('Supabase nao configurado');

      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: Linking.createURL('/'),
          skipBrowserRedirect: true,
        },
      });
      if (error) throw error;

      if (!data?.url) {
        throw new Error('Nenhuma URL de OAuth retornada');
      }

      const result = await WebBrowser.openAuthSessionAsync(
        data.url,
        Linking.createURL('/'),
        { showInRecents: true }
      );

      if (result.type === 'success') {
        const urlParams = result.url.split('#')[1] || result.url.split('?')[1];
        if (urlParams) {
          const paramsList = urlParams.split('&');
          let accessToken = null;
          let refreshToken = null;

          paramsList.forEach(param => {
            const [key, value] = param.split('=');
            if (key === 'access_token') accessToken = value;
            if (key === 'refresh_token') refreshToken = value;
          });

          if (accessToken && refreshToken) {
            const { error: sessionError } = await supabase.auth.setSession({
              access_token: accessToken,
              refresh_token: refreshToken,
            });
            if (sessionError) throw sessionError;
          }
        }
      }
    } catch (e) {
      Alert.alert('Erro', e.message || 'Falha no login com Google');
    } finally {
      setLoadingLogin(false);
    }
  };

  const handleLogin = async () => {
    if (!user || !pass) return Alert.alert('Erro', 'Preencha usuário e senha.');
    setLoadingLogin(true);

    try {
      if (isSignUp) {
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

      const url = `${normalizedServerUrl}/api/login`;
      const response = await fetchWithTimeout(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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
      const acaoCritica = !ligar; // Desligar dispositivos é ação crítica
      if (acaoCritica) {
        const okBio = await solicitarBiometria(`Confirme para desligar ${tipo}`);
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
          <View style={{ alignItems: 'center', marginBottom: 30 }}>
            <View style={styles.loginLogoWrap}>
              <Image source={appLogo} style={styles.loginLogoImage} resizeMode="contain" />
            </View>
            <Text style={{ fontSize: 28, fontWeight: 'bold', color: 'white' }}>ChickGuard</Text>
            <Text style={{ color: '#64748b' }}>{accessMode === 'viewer' ? 'Acesso Visitante' : 'Acesso Profissional'}</Text>
          </View>

          <View style={{ marginBottom: 20, width: '100%' }}>
             <Text style={styles.label}>ENDEREÇO DO SERVIDOR</Text>
             <TextInput 
               style={styles.input} 
               value={serverUrl} 
               onChangeText={setServerUrl} 
               placeholder="https://exemplo.trycloudflare.com" 
               placeholderTextColor="#64748b" 
               autoCapitalize='none'
               autoCorrect={false}
             />
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

          <TouchableOpacity style={{ marginTop: 15 }} onPress={() => setIsSignUp(!isSignUp)}>
            <Text style={{ color: '#10b981', textAlign: 'center' }}>
              {isSignUp ? 'Já tem uma conta? Fazer Login' : 'Não tem conta? Criar agora'}
            </Text>
          </TouchableOpacity>

          <View style={{ marginTop: 30, alignItems: 'center' }}>
            <Text style={{ color: '#64748b', marginBottom: 10 }}>Ou continue com</Text>
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
        <View style={{ backgroundColor: '#1e293b', padding: 24, borderRadius: 12, width: '85%', alignItems: 'center' }}>
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

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a"/>
      
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerBrand}>
          <Image source={appLogo} style={styles.headerLogo} resizeMode="contain" />
          <Text style={styles.appName}>ChickGuard AI</Text>
        </View>
        <Text style={{ color: '#10b981', fontSize: 10, fontWeight: 'bold' }}>ONLINE</Text>
      </View>

      {/* Conteúdo Dinâmico */}
      <View style={{ flex: 1 }}>
        {activeTab === 'monitor' && 
          <MonitorScreen 
            serverUrl={normalizedServerUrl}
            dados={dados} 
            loading={!dados}
            chickCount={chickCount}
            dispositivos={dispositivos}
            controlarDispositivo={controlarDispositivo}
            loadingAcao={loadingAcao}
            canControlDevices={canControlDevices}
            isOffline={isOffline}
            onOpenDigitalTwin={() => setActiveTab('digitalTwin')}
          />}
        {activeTab === 'digitalTwin' && allowedTabs.has('digitalTwin') &&
          <DigitalTwinScreen 
            serverUrl={normalizedServerUrl} 
            token={token} 
          />}
        {activeTab === 'birds' && allowedTabs.has('birds') && 
          <BirdsScreen 
            serverUrl={normalizedServerUrl} 
            token={token}
            enviarComandoVoz={enviarComandoVoz} 
            canControlDevices={canControlDevices}
          />}
        {activeTab === 'smart' && allowedTabs.has('smart') && 
          <SmartOpsScreen 
            serverUrl={normalizedServerUrl} 
            token={token} 
          />}
        {activeTab === 'management' && allowedTabs.has('management') && 
          <ManagementScreen 
            serverUrl={normalizedServerUrl} 
            token={token}
          />}
        {activeTab === 'alerts' && allowedTabs.has('alerts') && 
          <AlertsScreen 
            serverUrl={normalizedServerUrl} 
            token={token}
          />}
        {activeTab === 'history' && allowedTabs.has('history') && 
          <HistoryScreen 
            serverUrl={normalizedServerUrl} 
            token={token}
          />}
        {activeTab === 'system' && allowedTabs.has('system') && 
          <SystemScreen 
            serverUrl={normalizedServerUrl} 
            token={token}
          />}
        {activeTab === 'config' && allowedTabs.has('config') && 
          <ConfigScreen 
            serverUrl={serverUrl} 
            setServerUrl={(v) => setServerUrl(normalizeServerUrl(v) || v)} 
            logout={handleLogout} 
          />}
      </View>

      {/* Tab Bar (Menu Inferior) */}
      <View style={styles.tabBar}>
        {allowedTabs.has('monitor') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('monitor')}>
            <LayoutDashboard color={activeTab==='monitor'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='monitor'?'#10b981':'#64748b' }]}>Monitor</Text>
          </TouchableOpacity>
        )}

        {allowedTabs.has('digitalTwin') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('digitalTwin')}>
            <Layers color={activeTab==='digitalTwin'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='digitalTwin'?'#10b981':'#64748b' }]}>Gêmeo</Text>
          </TouchableOpacity>
        )}
        
        {allowedTabs.has('history') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('history')}>
            <History color={activeTab==='history'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='history'?'#10b981':'#64748b' }]}>Histórico</Text>
          </TouchableOpacity>
        )}

        {allowedTabs.has('birds') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('birds')}>
            <Bird color={activeTab==='birds'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='birds'?'#10b981':'#64748b' }]}>Aves</Text>
          </TouchableOpacity>
        )}

        {allowedTabs.has('smart') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('smart')}>
            <Activity color={activeTab==='smart'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='smart'?'#10b981':'#64748b' }]}>IA+IoT</Text>
          </TouchableOpacity>
        )}

        {allowedTabs.has('management') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('management')}>
            <Database color={activeTab==='management'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='management'?'#10b981':'#64748b' }]}>Gestão</Text>
          </TouchableOpacity>
        )}

        {allowedTabs.has('alerts') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('alerts')}>
            <Bell color={activeTab==='alerts'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='alerts'?'#10b981':'#64748b' }]}>Alertas</Text>
          </TouchableOpacity>
        )}

        {allowedTabs.has('system') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('system')}>
            <Cpu color={activeTab==='system'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='system'?'#10b981':'#64748b' }]}>Sistema</Text>
          </TouchableOpacity>
        )}

        {allowedTabs.has('config') && (
          <TouchableOpacity style={styles.tabItem} onPress={() => setActiveTab('config')}>
            <Settings color={activeTab==='config'?'#10b981':'#64748b'} size={22}/>
            <Text style={[styles.tabLabel, { color: activeTab==='config'?'#10b981':'#64748b' }]}>Ajustes</Text>
          </TouchableOpacity>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 30 },
  header: { padding: 20, borderBottomWidth: 1, borderBottomColor: '#1e293b', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: Platform.OS === 'ios' ? 10 : 30 },
  headerBrand: { flexDirection: 'row', alignItems: 'center' },
  headerLogo: { width: 30, height: 30, marginRight: 10, borderRadius: 6 },
  appName: { fontSize: 20, fontWeight: 'bold', color: 'white' },
  loginLogoWrap: { backgroundColor: 'rgba(16,185,129,0.1)', width: 104, height: 104, borderRadius: 99, marginBottom: 15, borderWidth: 1, borderColor: 'rgba(16,185,129,0.2)', alignItems: 'center', justifyContent: 'center' },
  loginLogoImage: { width: 72, height: 72 },
  loginModeRow: { flexDirection: 'row', gap: 10, marginBottom: 15, width: '100%' },
  loginModeBtn: { flex: 1, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: '#334155', alignItems: 'center', backgroundColor: '#1e293b' },
  loginModeBtnActive: { backgroundColor: 'rgba(16,185,129,0.2)', borderColor: 'rgba(16,185,129,0.4)' },
  loginModeBtnActiveBlue: { backgroundColor: 'rgba(59,130,246,0.2)', borderColor: 'rgba(59,130,246,0.4)' },
  loginModeText: { color: '#94a3b8', fontSize: 12, fontWeight: 'bold' },
  loginModeTextActive: { color: '#34d399' },
  loginModeTextActiveBlue: { color: '#93c5fd' },
  
  tabBar: { flexDirection: 'row', borderTopWidth: 1, borderTopColor: '#1e293b', backgroundColor: '#0f172a', paddingBottom: 20, paddingTop: 10 },
  tabItem: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  tabLabel: { fontSize: 8, marginTop: 4, fontWeight: 'bold' },

  inputContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1e293b', borderRadius: 12, paddingHorizontal: 15, marginBottom: 15, borderWidth: 1, borderColor: '#334155' },
  inputField: { flex: 1, color: 'white', padding: 15 },
  input: { backgroundColor: '#1e293b', color: 'white', padding: 15, borderRadius: 12, marginBottom: 20, borderWidth: 1, borderColor: '#334155' },
  label: { color: '#94a3b8', marginBottom: 10, fontSize: 12, fontWeight: 'bold' },
  
  btnGoogle: { backgroundColor: '#ffffff', padding: 15, borderRadius: 10, width: '100%', alignItems: 'center', borderColor: '#e2e8f0', borderWidth: 1 },
  btnGoogleText: { color: '#0f172a', fontWeight: 'bold' },
  btnPrimary: { backgroundColor: '#10b981', width: '100%', padding: 18, borderRadius: 16, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 10 },
  btnText: { color: 'white', fontWeight: 'bold', fontSize: 16 },
  button: { padding: 18, borderRadius: 16, alignItems: 'center' }
});
