import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, Text, View, ScrollView, ActivityIndicator 
} from 'react-native';

export default function AlertsScreen({ serverUrl }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const fetchAlerts = async () => {
      if (!serverUrl) {
        setLoading(false);
        return;
      }
      try {
        const req = await fetch(`${serverUrl}/api/alerts`);
        const json = await req.json();
        if (active) {
          setAlerts(json);
        }
      } catch (e) {
        console.warn('Error fetching alerts:', e);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchAlerts();
    const timer = setInterval(fetchAlerts, 3000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [serverUrl]);

  return (
    <View style={styles.container}>
      <Text style={styles.pageTitle}>Alertas do Sistema</Text>
      {loading ? (
        <ActivityIndicator size="large" color="#10b981" style={{ marginTop: 40 }} />
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {alerts.length === 0 && (
            <Text style={styles.emptyText}>Sem alertas ativos.</Text>
          )}
          {alerts.map((item, index) => (
            <View 
              key={`${item.id}-${index}`} 
              style={[
                styles.alertCard, 
                item.nivel === 'alto' 
                  ? styles.alertHigh 
                  : item.nivel === 'medio' 
                    ? styles.alertMedium 
                    : styles.alertLow
              ]}
            >
              <Text style={styles.alertType}>{item.tipo}</Text>
              <Text style={styles.alertMessage}>{item.mensagem}</Text>
              <Text style={styles.alertMeta}>{item.data} {item.hora}</Text>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  pageTitle: { fontSize: 22, fontWeight: 'bold', color: 'white', marginBottom: 20, marginTop: 10, marginLeft: 20 },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 20 },
  alertCard: { padding: 16, borderRadius: 12, marginBottom: 10, borderWidth: 1 },
  alertHigh: { backgroundColor: 'rgba(239,68,68,0.15)', borderColor: 'rgba(239,68,68,0.4)' },
  alertMedium: { backgroundColor: 'rgba(245,158,11,0.15)', borderColor: 'rgba(245,158,11,0.4)' },
  alertLow: { backgroundColor: '#1e293b', borderColor: '#334155' },
  alertType: { color: '#fff', fontWeight: 'bold', marginBottom: 6 },
  alertMessage: { color: '#cbd5e1', marginBottom: 8 },
  alertMeta: { color: '#94a3b8', fontSize: 12 },
  emptyText: { color: '#94a3b8', textAlign: 'center', marginTop: 40 }
});
