import React, { useState } from 'react';
import { 
  StyleSheet, Text, View, ScrollView, TouchableOpacity, 
  ActivityIndicator, Platform 
} from 'react-native';
import { WebView } from 'react-native-webview';
import { 
  Wind, Zap, CheckCircle, AlertTriangle, Bird, Layers 
} from 'lucide-react-native';

export default function MonitorScreen({ 
  serverUrl, dados, loading, chickCount, dispositivos, 
  controlarDispositivo, loadingAcao, canControlDevices, isOffline, 
  onOpenDigitalTwin 
}) {
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

      {/* Main Status Card */}
      <View style={[styles.mainCard, { backgroundColor: getStatusColor() }]}>
        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.cardLabel}>TEMPERATURA ATUAL</Text>
            {loading ? (
              <ActivityIndicator color="#fff" style={{ marginTop: 10 }} />
            ) : (
              <Text style={styles.tempText}>{dados?.temperatura}°C</Text>
            )}
          </View>
          <View style={styles.iconBox}>
            {dados?.status === 'NORMAL' ? (
              <CheckCircle size={32} color="#FFF" />
            ) : (
              <AlertTriangle size={32} color="#FFF" />
            )}
          </View>
        </View>
        <Text style={styles.statusTitle}>{dados?.status || "Conectando..."}</Text>
        <Text style={styles.statusMsg}>{dados?.mensagem || "Verificando sensores..."}</Text>
      </View>

      {/* Chick Count Card */}
      <View style={styles.countCard}>
        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.cardLabel}>AVES DETECTADAS</Text>
            <Text style={styles.countText}>{chickCount}</Text>
          </View>
          <View style={[styles.iconBox, { backgroundColor: 'rgba(16, 185, 129, 0.2)' }]}>
            <Bird size={32} color="#10b981" />
          </View>
        </View>
        <Text style={styles.statusMsg}>Contagem em tempo real via IA.</Text>
      </View>

      {/* Digital Twin Shortcut Card */}
      <TouchableOpacity 
        style={styles.digitalTwinShortcut} 
        onPress={onOpenDigitalTwin}
      >
        <Layers size={24} color="#10b981" />
        <View style={styles.shortcutTextContainer}>
          <Text style={styles.shortcutTitle}>Gêmeo Digital 2D</Text>
          <Text style={styles.shortcutSubtitle}>Visualizar mapa térmico, densidade e status IoT</Text>
        </View>
      </TouchableOpacity>

      {/* Video Streaming */}
      <Text style={styles.sectionTitle}>Transmissão da Câmera</Text>
      <View style={styles.videoContainer}>
        {!hasValidServer ? (
          <View style={styles.tunnelBlockerContainer}>
            <AlertTriangle size={32} color="#f59e0b" />
            <Text style={styles.tunnelTitle}>Servidor não configurado</Text>
            <Text style={styles.tunnelText}>Defina uma URL válida em Ajustes.</Text>
          </View>
        ) : (
          <WebView 
            source={{ uri: videoUrl }} 
            style={{ flex: 1, backgroundColor: 'black' }}
            scrollEnabled={true}
            nestedScrollEnabled={true}
            onError={(e) => {
              const desc = e?.nativeEvent?.description || 'Falha ao carregar vídeo';
              setVideoError(desc);
            }}
          />
        )}
        <View style={styles.liveBadge}>
          <Text style={styles.liveText}>AO VIVO</Text>
        </View>
      </View>
      
      {!!videoError && (
        <Text style={styles.errorText}>
          Vídeo indisponível: {videoError}. Verifique se o túnel ainda está ativo.
        </Text>
      )}

      {/* Controls Grid */}
      <Text style={styles.sectionTitle}>Controlo Ambiental</Text>
      <View style={styles.actionGrid}>
        <TouchableOpacity 
          style={[
            styles.actionButton, 
            dispositivos.ventilacao && styles.actionButtonActiveBlue, 
            !canControlDevices && styles.actionButtonDisabled
          ]} 
          onPress={() => controlarDispositivo('ventilacao', !dispositivos.ventilacao)}
          disabled={loadingAcao || !canControlDevices}
        >
          <Wind size={24} color={dispositivos.ventilacao ? "#fff" : "#3b82f6"} />
          <Text style={[styles.actionLabel, dispositivos.ventilacao && { color: '#fff' }]}>Ventilação</Text>
          <Text style={[styles.actionStatus, dispositivos.ventilacao && { color: 'rgba(255,255,255,0.7)' }]}>
            {dispositivos.ventilacao ? 'LIGADO' : 'DESLIGADO'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={[
            styles.actionButton, 
            dispositivos.aquecedor && styles.actionButtonActiveOrange, 
            !canControlDevices && styles.actionButtonDisabled
          ]} 
          onPress={() => controlarDispositivo('aquecedor', !dispositivos.aquecedor)}
          disabled={loadingAcao || !canControlDevices}
        >
          <Zap size={24} color={dispositivos.aquecedor ? "#fff" : "#f97316"} />
          <Text style={[styles.actionLabel, dispositivos.aquecedor && { color: '#fff' }]}>Aquecedor</Text>
          <Text style={[styles.actionStatus, dispositivos.aquecedor && { color: 'rgba(255,255,255,0.7)' }]}>
            {dispositivos.aquecedor ? 'LIGADO' : 'DESLIGADO'}
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollContent: { padding: 20, paddingBottom: 30 },
  offlineBanner: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: 'rgba(245,158,11,0.2)', 
    padding: 12, 
    borderRadius: 12, 
    marginBottom: 20, 
    borderWidth: 1, 
    borderColor: 'rgba(245,158,11,0.5)' 
  },
  offlineText: { color: '#f59e0b', fontWeight: 'bold', marginLeft: 10, fontSize: 13 },
  mainCard: { padding: 24, borderRadius: 24, marginBottom: 20 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardLabel: { color: 'rgba(255,255,255,0.7)', fontSize: 12, fontWeight: 'bold' },
  tempText: { fontSize: 56, fontWeight: 'bold', color: '#FFF' },
  iconBox: { 
    backgroundColor: 'rgba(255,255,255,0.1)', 
    padding: 12, 
    borderRadius: 16, 
    borderWidth: 1, 
    borderColor: 'rgba(255,255,255,0.2)' 
  },
  statusTitle: { fontSize: 20, fontWeight: 'bold', color: 'white', marginTop: 10 },
  statusMsg: { color: 'rgba(255,255,255,0.9)', marginTop: 5 },
  countCard: { padding: 20, borderRadius: 24, marginBottom: 20, backgroundColor: '#1e293b' },
  countText: { fontSize: 48, fontWeight: 'bold', color: '#FFF', letterSpacing: -2 },
  
  digitalTwinShortcut: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    borderColor: '#334155',
    borderWidth: 1,
    borderRadius: 20,
    padding: 16,
    marginBottom: 20,
    gap: 14
  },
  shortcutTextContainer: { flex: 1 },
  shortcutTitle: { color: 'white', fontSize: 16, fontWeight: 'bold' },
  shortcutSubtitle: { color: '#94a3b8', fontSize: 12, marginTop: 2 },

  sectionTitle: { 
    color: '#94a3b8', 
    fontSize: 12, 
    fontWeight: 'bold', 
    marginBottom: 10, 
    textTransform: 'uppercase', 
    letterSpacing: 0.5 
  },
  videoContainer: { 
    height: 220, 
    backgroundColor: 'black', 
    borderRadius: 16, 
    overflow: 'hidden', 
    borderWidth: 1, 
    borderColor: '#334155', 
    marginBottom: 20, 
    position: 'relative' 
  },
  tunnelBlockerContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#1e293b', padding: 20 },
  tunnelTitle: { color: 'white', fontSize: 16, fontWeight: 'bold', marginTop: 10, marginBottom: 5 },
  tunnelText: { color: '#94a3b8', fontSize: 12, textAlign: 'center' },
  liveBadge: { 
    position: 'absolute', 
    top: 10, 
    left: 10, 
    backgroundColor: '#ef4444', 
    paddingHorizontal: 8, 
    paddingVertical: 4, 
    borderRadius: 4 
  },
  liveText: { color: 'white', fontSize: 10, fontWeight: 'bold' },
  errorText: { color: '#fca5a5', fontSize: 12, marginBottom: 12 },
  
  actionGrid: { flexDirection: 'row', gap: 15 },
  actionButton: { 
    flex: 1, 
    backgroundColor: '#1e293b', 
    padding: 15, 
    borderRadius: 20, 
    alignItems: 'center', 
    borderWidth: 1, 
    borderColor: '#334155' 
  },
  actionButtonDisabled: { opacity: 0.5 },
  actionButtonActiveBlue: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  actionButtonActiveOrange: { backgroundColor: '#f97316', borderColor: '#f97316' },
  actionLabel: { color: '#cbd5e1', marginTop: 10, fontWeight: 'bold', fontSize: 12 },
  actionStatus: { color: '#94a3b8', marginTop: 5, fontSize: 10, fontWeight: 'bold' }
});
