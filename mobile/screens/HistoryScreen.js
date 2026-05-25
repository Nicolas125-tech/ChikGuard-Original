import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, Text, View, ScrollView, ActivityIndicator 
} from 'react-native';

export default function HistoryScreen({ serverUrl }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const fetchHistory = async () => {
      if (!serverUrl) {
        setLoading(false);
        return;
      }
      try {
        const req = await fetch(`${serverUrl}/api/history`);
        const json = await req.json();
        if (active) {
          setHistory(json);
        }
      } catch (e) {
        console.warn('Error fetching history:', e);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchHistory();
    return () => { active = false; };
  }, [serverUrl]);

  return (
    <View style={styles.container}>
      <Text style={styles.pageTitle}>Histórico de Eventos</Text>
      {loading ? (
        <ActivityIndicator size="large" color="#10b981" style={{ marginTop: 40 }} />
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {history.map((item, index) => (
            <View key={`history-${index}`} style={styles.historyItem}>
              <View style={[styles.historyDot, { backgroundColor: item.status === 'NORMAL' ? '#10b981' : '#ef4444' }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.historyTemp}>{item.temp}°C - {item.status}</Text>
                <Text style={styles.historyDate}>{item.data} às {item.hora}</Text>
              </View>
            </View>
          ))}
          {history.length === 0 && (
            <Text style={styles.emptyText}>Nenhum dado gravado.</Text>
          )}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  pageTitle: { fontSize: 22, fontWeight: 'bold', color: 'white', marginBottom: 20, marginTop: 10, marginLeft: 20 },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 20 },
  historyItem: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: '#1e293b', 
    padding: 15, 
    borderRadius: 12, 
    marginBottom: 10 
  },
  historyDot: { width: 10, height: 10, borderRadius: 5, marginRight: 15 },
  historyTemp: { color: 'white', fontWeight: 'bold', fontSize: 16 },
  historyDate: { color: '#94a3b8', fontSize: 12 },
  emptyText: { color: '#64748b', textAlign: 'center', marginTop: 40 }
});
