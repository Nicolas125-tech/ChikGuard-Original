import React, { useState, useEffect, useCallback } from 'react';
import { 
  StyleSheet, Text, View, ScrollView, TouchableOpacity, 
  ActivityIndicator, TextInput, Image, Alert 
} from 'react-native';
import { Cpu, Save, History } from 'lucide-react-native';

const MetricCard = ({ label, value }) => (
  <View style={styles.metricCard}>
    <Text style={styles.metricLabel}>{label}</Text>
    <Text style={styles.metricValue}>{value}</Text>
  </View>
);

export default function SmartOpsScreen({ serverUrl, token }) {
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
    if (!serverUrl) return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [bReq, iReq, sReq, aReq, btReq, cReq, lReq] = await Promise.all([
        fetch(`${serverUrl}/api/behavior/live`, { headers }),
        fetch(`${serverUrl}/api/immobility/live`, { headers }),
        fetch(`${serverUrl}/api/sensors/live`, { headers }),
        fetch(`${serverUrl}/api/auto-mode`, { headers }),
        fetch(`${serverUrl}/api/batches`, { headers }),
        fetch(`${serverUrl}/api/cameras`, { headers }),
        fetch(`${serverUrl}/api/logbook?limit=20`, { headers })
      ]);

      if (bReq.ok) setBehavior(await bReq.json());
      if (iReq.ok) setImmobility(await iReq.json());
      if (sReq.ok) setSensors(await sReq.json());
      if (aReq.ok) setAutoMode(await aReq.json());
      if (btReq.ok) setBatches(await btReq.json());
      if (cReq.ok) setCameras(await cReq.json());
      if (lReq.ok) setLogbook(await lReq.json());
    } catch (e) {
      console.warn('Error loading smart data:', e);
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
      const req = await fetch(`${serverUrl}/api/auto-mode`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ enabled: !autoMode.enabled })
      });
      if (req.ok) {
        loadSmartData();
      } else {
        Alert.alert('Erro', 'Falha ao atualizar modo automático.');
      }
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
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: batchName, start_date: batchStartDate, active: true })
      });
      if (!req.ok) {
        const err = await req.json();
        throw new Error(err.msg || 'Falha ao criar lote');
      }
      setBatchName('');
      setBatchStartDate('');
      loadSmartData();
      Alert.alert('Sucesso', 'Lote criado e ativado!');
    } catch (e) {
      Alert.alert('Erro', e.message || 'Falha ao criar lote.');
    }
  };

  const generateReport = async () => {
    try {
      const req = await fetch(`${serverUrl}/api/reports/weekly`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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
      const req = await fetch(`${serverUrl}/api/logbook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ note: logNote, author: 'tratador-mobile' })
      });
      if (req.ok) {
        setLogNote('');
        loadSmartData();
      } else {
        Alert.alert('Erro', 'Falha ao salvar nota do lote.');
      }
    } catch (e) {
      Alert.alert('Erro', 'Falha ao salvar nota do lote.');
    }
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#10b981" />
      </View>
    );
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
        <View style={styles.rowItem}>
          <Text style={styles.rowTitle}>Temperatura</Text>
          <Text style={styles.rowMeta}>{sensors?.temperature_c ?? '--'} °C</Text>
        </View>
        <View style={styles.rowItem}>
          <Text style={styles.rowTitle}>Umidade</Text>
          <Text style={styles.rowMeta}>{sensors?.humidity_pct ?? '--'} %</Text>
        </View>
        <View style={styles.rowItem}>
          <Text style={styles.rowTitle}>Amônia</Text>
          <Text style={styles.rowMeta}>{sensors?.ammonia_ppm ?? '--'} ppm</Text>
        </View>
        <View style={styles.rowItem}>
          <Text style={styles.rowTitle}>Ração</Text>
          <Text style={[
            styles.rowMeta, 
            (Number(sensors?.feed_level_pct ?? 100) < 20) && styles.warningText
          ]}>
            {sensors?.feed_level_pct ?? '--'} %
          </Text>
        </View>
        <View style={styles.rowItem}>
          <Text style={styles.rowTitle}>Água</Text>
          <Text style={styles.rowMeta}>{sensors?.water_level_pct ?? '--'} %</Text>
        </View>
      </View>

      <TouchableOpacity style={styles.btnPrimary} onPress={toggleAutoMode}>
        <Cpu color="#fff" size={20} />
        <Text style={styles.btnText}>
          {autoMode?.enabled ? 'Desativar Piloto Automático' : 'Ativar Piloto Automático'}
        </Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Heatmap Diário</Text>
      <View style={styles.heatmapCard}>
        {serverUrl ? (
          <Image source={{ uri: heatmapUrl }} style={styles.heatmapImage} resizeMode="cover" />
        ) : (
          <Text style={styles.emptyText}>Servidor não configurado</Text>
        )}
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
        <TouchableOpacity style={styles.btnSecondary} onPress={createBatch}>
          <Save color="#fff" size={18} />
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
        <TouchableOpacity style={styles.btnSecondary} onPress={generateReport}>
          <History color="#fff" size={18} />
          <Text style={styles.btnText}>Gerar Relatório Semanal (PDF)</Text>
        </TouchableOpacity>
        {!!reportMsg && <Text style={styles.reportPathText}>{reportMsg}</Text>}
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
        <TouchableOpacity style={styles.btnSecondary} onPress={saveLogbook}>
          <Save color="#fff" size={18} />
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
    marginBottom: 16,
    padding: 10
  },
  rowItem: { padding: 12, borderBottomColor: '#334155', borderBottomWidth: 1, flexDirection: 'row', justifyContent: 'space-between', flexWrap: 'wrap' },
  rowTitle: { color: 'white', fontWeight: 'bold' },
  rowMeta: { color: '#94a3b8', fontSize: 12 },
  rowDate: { color: '#64748b', fontSize: 11, width: '100%', marginTop: 4 },
  warningText: { color: '#ef4444', fontWeight: 'bold' },
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
  btnSecondary: { 
    backgroundColor: '#3b82f6', 
    width: '100%', 
    padding: 14, 
    borderRadius: 12, 
    alignItems: 'center', 
    flexDirection: 'row', 
    justifyContent: 'center', 
    gap: 8,
    marginVertical: 10 
  },
  btnText: { color: 'white', fontWeight: 'bold', fontSize: 15 },
  heatmapCard: { 
    height: 220, 
    backgroundColor: '#111827', 
    borderRadius: 16, 
    overflow: 'hidden', 
    borderWidth: 1, 
    borderColor: '#334155', 
    marginBottom: 20,
    justifyContent: 'center',
    alignItems: 'center'
  },
  heatmapImage: { width: '100%', height: '100%' },
  emptyText: { color: '#94a3b8', textAlign: 'center' },
  input: { 
    backgroundColor: '#0f172a', 
    color: 'white', 
    padding: 14, 
    borderRadius: 10, 
    marginBottom: 12, 
    borderWidth: 1, 
    borderColor: '#334155' 
  },
  reportPathText: { color: '#10b981', fontSize: 12, marginTop: 8, paddingHorizontal: 10 }
});
