import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, Text, View, ScrollView, ActivityIndicator 
} from 'react-native';

const MetricCard = ({ label, value }) => (
  <View style={styles.metricCard}>
    <Text style={styles.metricLabel}>{label}</Text>
    <Text style={styles.metricValue}>{value}</Text>
  </View>
);

export default function SystemScreen({ serverUrl, token }) {
  const [summary, setSummary] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const loadSystemData = async () => {
      if (!serverUrl) {
        setLoading(false);
        return;
      }
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [summaryReq, infoReq] = await Promise.all([
          fetch(`${serverUrl}/api/summary`, { headers }),
          fetch(`${serverUrl}/api/system-info`, { headers })
        ]);
        if (active) {
          if (summaryReq.ok) setSummary(await summaryReq.json());
          if (infoReq.ok) setSystemInfo(await infoReq.json());
        }
      } catch (e) {
        console.warn('Error loading system data:', e);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    
    loadSystemData();
    const timer = setInterval(loadSystemData, 3000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [serverUrl]);

  const uptime = systemInfo 
    ? `${Math.floor(systemInfo.uptime_seconds / 3600)}h ${Math.floor((systemInfo.uptime_seconds % 3600) / 60)}m` 
    : "--";

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#10b981" />
      </View>
    );
  }

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
}

const styles = StyleSheet.create({
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f172a' },
  scrollContent: { padding: 20, paddingBottom: 30 },
  pageTitle: { fontSize: 22, fontWeight: 'bold', color: 'white', marginBottom: 20, marginTop: 10 },
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  metricCard: { 
    width: '48%', 
    backgroundColor: '#1e293b', 
    borderColor: '#334155', 
    borderWidth: 1, 
    borderRadius: 12, 
    padding: 14 
  },
  metricLabel: { color: '#94a3b8', fontSize: 11, marginBottom: 6 },
  metricValue: { color: 'white', fontSize: 20, fontWeight: 'bold' }
});
