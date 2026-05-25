import React, { useState, useEffect, useCallback } from 'react';
import { 
  StyleSheet, Text, View, ScrollView, TouchableOpacity, 
  ActivityIndicator 
} from 'react-native';
import { Bird, Activity } from 'lucide-react-native';

const MetricCard = ({ label, value }) => (
  <View style={styles.metricCard}>
    <Text style={styles.metricLabel}>{label}</Text>
    <Text style={styles.metricValue}>{value}</Text>
  </View>
);

export default function BirdsScreen({ serverUrl, enviarComandoVoz, canControlDevices }) {
  const [live, setLive] = useState({ count: 0, items: [] });
  const [registry, setRegistry] = useState({ count: 0, items: [] });
  const [selectedBird, setSelectedBird] = useState(null);
  const [path, setPath] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadBirds = useCallback(async () => {
    if (!serverUrl) return;
    try {
      const [liveReq, regReq] = await Promise.all([
        fetch(`${serverUrl}/api/birds/live`),
        fetch(`${serverUrl}/api/birds/registry?limit=500`),
      ]);
      if (liveReq.ok) setLive(await liveReq.json());
      if (regReq.ok) setRegistry(await regReq.json());
    } catch (e) {
      console.warn('Error loading birds:', e);
    } finally {
      setLoading(false);
    }
  }, [serverUrl]);

  const loadPath = useCallback(async (birdUid) => {
    if (!serverUrl) return;
    try {
      const req = await fetch(`${serverUrl}/api/birds/path/${birdUid}?limit=200`);
      if (!req.ok) {
        setPath([]);
        return;
      }
      const json = await req.json();
      setPath(json.items || []);
    } catch (e) {
      console.warn('Error loading path:', e);
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
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#10b981" />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.pageTitle}>Aves Vistas</Text>

      <View style={styles.metricsGrid}>
        <MetricCard label="Visíveis agora" value={live.count ?? 0} />
        <MetricCard label="Aves únicas" value={registry.count ?? 0} />
        <MetricCard label="ID selecionado" value={selectedBird ?? "--"} />
      </View>

      {!canControlDevices && (
        <Text style={styles.visitorWarning}>
          Perfil visitante: controles desativados.
        </Text>
      )}

      <Text style={styles.sectionTitle}>Aves vivas no quadro</Text>
      <View style={styles.listCard}>
        {live.items?.length === 0 && (
          <Text style={styles.emptyText}>Nenhuma ave visível.</Text>
        )}
        {live.items?.map((item) => (
          <TouchableOpacity 
            key={`live-${item.bird_uid}`} 
            style={styles.rowItem} 
            onPress={() => setSelectedBird(item.bird_uid)}
          >
            <Text style={styles.rowTitle}>ID {item.bird_uid}</Text>
            <Text style={styles.rowMeta}>Conf {item.confidence} | track {item.track_id}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Registro persistente</Text>
      <View style={styles.listCard}>
        {registry.items?.length === 0 && (
          <Text style={styles.emptyText}>Sem aves registradas.</Text>
        )}
        {registry.items?.map((item) => (
          <TouchableOpacity 
            key={`reg-${item.bird_uid}`} 
            style={styles.rowItem} 
            onPress={() => setSelectedBird(item.bird_uid)}
          >
            <Text style={styles.rowTitle}>ID {item.bird_uid}</Text>
            <Text style={styles.rowMeta}>Vezes {item.sightings} | Conf max {item.max_confidence}</Text>
            <Text style={styles.rowDate}>Última vez: {item.last_seen}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Trilha da ave selecionada</Text>
      <View style={styles.listCard}>
        {selectedBird === null && (
          <Text style={styles.emptyText}>Toque em uma ave para carregar a trilha.</Text>
        )}
        {selectedBird !== null && path.length === 0 && (
          <Text style={styles.emptyText}>Sem trilha para o ID {selectedBird}.</Text>
        )}
        {path.slice(-20).map((point) => (
          <View key={`path-${point.id}`} style={styles.rowItem}>
            <Text style={styles.rowTitle}>({point.x}, {point.y})</Text>
            <Text style={styles.rowDate}>{point.timestamp}</Text>
          </View>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Comandos de Voz</Text>
      <TouchableOpacity 
        style={[styles.btnPrimary, !canControlDevices && styles.btnDisabled]} 
        onPress={enviarComandoVoz} 
        disabled={!enviarComandoVoz || !canControlDevices}
      >
        <Activity color="#fff" size={20} />
        <Text style={styles.btnText}>Microfone: comandos rápidos</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f172a' },
  scrollContent: { padding: 20, paddingBottom: 30 },
  pageTitle: { fontSize: 22, fontWeight: 'bold', color: 'white', marginBottom: 20, marginTop: 10 },
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 10 },
  metricCard: { 
    width: '31%', 
    backgroundColor: '#1e293b', 
    borderColor: '#334155', 
    borderWidth: 1, 
    borderRadius: 12, 
    padding: 10 
  },
  metricLabel: { color: '#94a3b8', fontSize: 10, marginBottom: 4 },
  metricValue: { color: 'white', fontSize: 16, fontWeight: 'bold' },
  visitorWarning: { color: '#94a3b8', fontSize: 12, marginTop: 8, marginBottom: 15 },
  sectionTitle: { 
    color: '#94a3b8', 
    fontSize: 12, 
    fontWeight: 'bold', 
    marginBottom: 10, 
    textTransform: 'uppercase', 
    letterSpacing: 0.5,
    marginTop: 15
  },
  listCard: { 
    backgroundColor: '#1e293b', 
    borderColor: '#334155', 
    borderWidth: 1, 
    borderRadius: 12, 
    overflow: 'hidden', 
    marginBottom: 16 
  },
  rowItem: { padding: 12, borderBottomColor: '#334155', borderBottomWidth: 1 },
  rowTitle: { color: 'white', fontWeight: 'bold' },
  rowMeta: { color: '#94a3b8', fontSize: 12, marginTop: 2 },
  rowDate: { color: '#64748b', fontSize: 11, marginTop: 2 },
  emptyText: { color: '#94a3b8', textAlign: 'center', padding: 14 },
  btnPrimary: { 
    backgroundColor: '#10b981', 
    width: '100%', 
    padding: 18, 
    borderRadius: 16, 
    alignItems: 'center', 
    flexDirection: 'row', 
    justifyContent: 'center', 
    gap: 10,
    marginTop: 10 
  },
  btnDisabled: { backgroundColor: '#334155', opacity: 0.6 },
  btnText: { color: 'white', fontWeight: 'bold', fontSize: 16 }
});
