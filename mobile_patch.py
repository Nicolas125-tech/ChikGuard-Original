import re

with open('mobile/App.js', 'r') as f:
    content = f.read()

# Make sure imports are there
if 'import * as Notifications from' not in content:
    content = content.replace("import React, { useState, useEffect, useCallback } from 'react';",
    "import React, { useState, useEffect, useCallback } from 'react';\nimport * as Notifications from 'expo-notifications';")

# Add Offline Mode to Monitor Screen & FCM Registration stub
monitor_old = '''const MonitorScreen = ({ serverUrl, dados, loading, chickCount, dispositivos, controlarDispositivo, loadingAcao, enviarComandoVoz, canControlDevices }) => {'''
monitor_new = '''const MonitorScreen = ({ serverUrl, dados, loading, chickCount, dispositivos, controlarDispositivo, loadingAcao, enviarComandoVoz, canControlDevices }) => {
  const [offlineMode, setOfflineMode] = useState(false);
  const [offlineDados, setOfflineDados] = useState(null);

  useEffect(() => {
    if (dados) {
      setOfflineMode(false);
      AsyncStorage.setItem('cg_last_dados', JSON.stringify(dados));
    } else if (!loading) {
      setOfflineMode(true);
      AsyncStorage.getItem('cg_last_dados').then(d => {
        if(d) setOfflineDados(JSON.parse(d));
      });
    }
  }, [dados, loading]);

  const displayDados = dados || offlineDados;
'''
if 'const [offlineMode' not in content:
    content = content.replace(monitor_old, monitor_new)

# Replace dados occurrences inside MonitorScreen
render_old = '''      {/* Card Principal */}
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
      </View>'''

render_new = '''      {/* Card Principal */}
      <View style={[styles.mainCard, { backgroundColor: getStatusColor() }]}>
        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.cardLabel}>TEMPERATURA ATUAL</Text>
            {loading && !offlineMode ? <ActivityIndicator color="#fff"/> :
              <Text style={styles.tempText}>{displayDados?.temperatura}°C</Text>
            }
          </View>
          <View style={styles.iconBox}>
            {displayDados?.status === 'NORMAL' ? <CheckCircle size={32} color="#FFF"/> : <AlertTriangle size={32} color="#FFF"/>}
          </View>
        </View>
        <Text style={styles.statusTitle}>{displayDados?.status || "Conectando..."}</Text>
        <Text style={styles.statusMsg}>{displayDados?.mensagem || "Verificando sensores..."}</Text>
        {offlineMode && <Text style={{color:'yellow', fontSize: 12, marginTop: 10}}>Modo Offline (Ultima Leitura)</Text>}
      </View>'''

if 'displayDados?.temperatura' not in content:
    content = content.replace(render_old, render_new)
    content = content.replace('''if (!dados) return "#334155";
    if (dados.status === 'CALOR') return "#dc2626";
    if (dados.status === 'FRIO') return "#2563eb";''', '''if (!displayDados) return "#334155";
    if (displayDados.status === 'CALOR') return "#dc2626";
    if (displayDados.status === 'FRIO') return "#2563eb";''')

# Add Biometric Bypass Login
check_login_old = '''  useEffect(() => {
    // Carregar dados salvos
    AsyncStorage.multiGet(['cg_token', 'cg_server_url', 'cg_role', 'cg_username']).then(values => {
      if(values[0][1]) setToken(values[0][1]);
      if(values[1][1]) setServerUrl(normalizeServerUrl(values[1][1]) || values[1][1]);
      if(values[2][1]) setRole(values[2][1] || 'admin');
      if(values[3][1]) setUsername(values[3][1] || '');
    });
  }, []);'''

check_login_new = '''  useEffect(() => {
    // FCM Setup stub
    const registerForPushNotificationsAsync = async () => {
      try {
        let token;
        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;
        if (existingStatus !== 'granted') {
          const { status } = await Notifications.requestPermissionsAsync();
          finalStatus = status;
        }
        if (finalStatus !== 'granted') return;
        token = (await Notifications.getExpoPushTokenAsync()).data;
      } catch (e) {}
    };
    registerForPushNotificationsAsync();
  }, []);

  useEffect(() => {
    // Carregar dados salvos e tentar login biometrico automatico
    const loadAndAuth = async () => {
      const values = await AsyncStorage.multiGet(['cg_token', 'cg_server_url', 'cg_role', 'cg_username']);
      if(values[0][1]) {
        // Has previous token, try face id
        try {
          const hasHardware = await LocalAuthentication.hasHardwareAsync();
          const isEnrolled = await LocalAuthentication.isEnrolledAsync();
          if (hasHardware && isEnrolled) {
             const result = await LocalAuthentication.authenticateAsync({
                promptMessage: 'Desbloquear ChikGuard',
                cancelLabel: 'Cancelar'
             });
             if (!result.success) {
                 // failed to unlock
                 return;
             }
          }
        } catch(e) {}
        setToken(values[0][1]);
        if(values[1][1]) setServerUrl(normalizeServerUrl(values[1][1]) || values[1][1]);
        if(values[2][1]) setRole(values[2][1] || 'admin');
        if(values[3][1]) setUsername(values[3][1] || '');
      }
    };
    loadAndAuth();
  }, []);'''

if 'registerForPushNotificationsAsync' not in content:
    content = content.replace(check_login_old, check_login_new)

with open('mobile/App.js', 'w') as f:
    f.write(content)
