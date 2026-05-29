import React, { useState, useEffect, useCallback } from 'react';
import { 
  StyleSheet, Text, View, ScrollView, ActivityIndicator 
} from 'react-native';

const MetricCard = ({ label, value }) => (
  <View style={styles.metricCard}>
    <Text style={styles.metricLabel}>{label}</Text>
    <Text style={styles.metricValue}>{value}</Text>
  </View>
);

export default function ManagementScreen({ serverUrl, token }) {
  const [weightLive, setWeightLive] = useState(null);
  const [acoustic, setAcoustic] = useState(null);
  const [acousticModel, setAcousticModel] = useState(null);
  const [thermal, setThermal] = useState({ count: 0, sectors: [], items: [] });
  const [energy, setEnergy] = useState(null);
  const [audit, setAudit] = useState({ count: 0, items: [] });
  const [sync, setSync] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadManagementData = useCallback(async () => {
    if (!serverUrl) return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [w, a, m, t, e, au, s] = await Promise.all([
        fetch(`${serverUrl}/api/weight/live`, { headers }),
        fetch(`${serverUrl}/api/acoustic/live`, { headers }),
        fetch(`${serverUrl}/api/acoustic/model-info`, { headers }),
        fetch(`${serverUrl}/api/thermal-anomalies/live?minutes=60`, { headers }),
        fetch(`${serverUrl}/api/energy/summary`, { headers }),
        fetch(`${serverUrl}/api/audit/logs?limit=40`, { headers }),
        fetch(`${serverUrl}/api/sync/status`, { headers })
      ]);
      if (w.ok) setWeightLive(await w.json());
      if (a.ok) setAcoustic(await a.json());
      if (m.ok) setAcousticModel(await m.json());
      if (t.ok) setThermal(await t.json());
      if (e.ok) setEnergy(await e.json());
      if (au.ok) setAudit(await au.json());
      if (s.ok) setSync(await s.json());
    } catch (e) {
      console.warn('Error loading management data:', e);
    } finally {
      setLoading(false);
    }
  }, [serverUrl]);

  useEffect(() => {
    loadManagementData();
    const timer = setInterval(loadManagementData, 5000);
    return () => clearInterval(timer);
  }, [loadManagementData]);

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#10b981" />
      </View>
    );
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
          <Text style={styles.rowMeta}>{acousticModel?.loaded ? 'CARREGADO' : 'NÃO CARREGADO'}</Text>
          {!!acousticModel?.last_error && (
            <Text style={styles.rowDate}>{acousticModel.last_error}</Text>
          )}
        </View>
      </View>

      <Text style={styles.sectionTitle}>Anomalias térmicas</Text>
      <View style={styles.listCard}>
        <View style={styles.summaryRow}>
          <Text style={styles.rowMeta}>
            Detectadas: {thermal.count || 0} | Setores: {(thermal.sectors || []).join(', ') || '--'}
          </Text>
        </View>
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
}

const styles = StyleSheet.create({
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f172a' },
  scrollContent: { padding: 20, paddingBottom: 40 },
  pageTitle: { fontSize: 22, fontWeight: 'bold', color: 'white', marginBottom: 20, marginTop: 10 },
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 15 },
  metricCard: { 
    width: '48%', 
    backgroundColor: '#1e293b', 
    borderColor: '#334155', 
    borderWidth: 1, 
    borderRadius: 12, 
    padding: 14 
  },
  metricLabel: { color: '#94a3b8', fontSize: 11, marginBottom: 6 },
  metricValue: { color: 'white', fontSize: 20, fontWeight: 'bold' },
  sectionTitle: { 
    color: '#94a3b8', 
    fontSize: 12, 
    fontWeight: 'bold', 
    marginBottom: 10, 
    textTransform: 'uppercase', 
    letterSpacing: 0.5,
    marginTop: 20
  },
  listCard: { 
    backgroundColor: '#1e293b', 
    borderColor: '#334155', 
    borderWidth: 1, 
    borderRadius: 16, 
    overflow: 'hidden', 
    marginBottom: 16 
  },
  rowItem: { padding: 12, borderBottomColor: '#334155', borderBottomWidth: 1 },
  rowTitle: { color: 'white', fontWeight: 'bold' },
  rowMeta: { color: '#94a3b8', fontSize: 12, marginTop: 2 },
  rowDate: { color: '#64748b', fontSize: 11, marginTop: 2 },
  summaryRow: { padding: 12, borderBottomColor: '#334155', borderBottomWidth: 1 }
});
