import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, ActivityIndicator, Alert, StyleSheet } from 'react-native';
import { Picker } from '@react-native-picker/picker';

export default function AdminPanel({ serverIP, token }) {
  const [pendingUsers, setPendingUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRoles, setSelectedRoles] = useState({});

  const fetchPendingUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${serverIP}/api/admin/pending-users`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const d = await res.json();
        const users = d.items || [];
        setPendingUsers(users);
        const initialRoles = {};
        users.forEach(u => initialRoles[u.id] = 'VIEWER');
        setSelectedRoles(initialRoles);
      } else {
        Alert.alert('Erro', 'Nao foi possivel carregar utilizadores pendentes.');
      }
      setLoading(false);
    } catch (e) {
      console.error(e);
      Alert.alert('Erro', 'Acesso negado ou erro ao buscar utilizadores.');
      setLoading(false);
    }
  };

  useEffect(() => {
    setTimeout(fetchPendingUsers, 0);
  }, []);

  const handleApprove = async (userId) => {
    const targetRole = selectedRoles[userId] || 'VIEWER';

    Alert.alert(
      "Confirmar Aprovação",
      `Deseja aprovar o utilizador como ${targetRole}?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Aprovar",
          onPress: async () => {
            try {
              const res = await fetch(`${serverIP}/api/admin/approve-user`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ target_user_id: userId, target_role: targetRole })
              });

              if (!res.ok) {
                const d = await res.json();
                Alert.alert('Erro', `Falha ao aprovar: ${d.msg || d.error || 'Desconhecido'}`);
                return;
              }
              Alert.alert('Sucesso', 'Utilizador aprovado com sucesso!');
              setPendingUsers(prev => prev.filter(user => user.id !== userId));
            } catch (e) {
              Alert.alert('Erro de rede', e.message);
            }
          }
        }
      ]
    );
  };

  const renderItem = ({ item }) => (
    <View style={styles.card}>
      <Text style={styles.emailText}>{item.email}</Text>
      <Text style={styles.idText}>ID: {item.id.substring(0, 8)}...</Text>
      <Text style={styles.dateText}>Registado: {new Date(item.created_at).toLocaleDateString()}</Text>

      <View style={styles.actionRow}>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={selectedRoles[item.id]}
            style={styles.picker}
            onValueChange={(itemValue) =>
              setSelectedRoles({ ...selectedRoles, [item.id]: itemValue })
            }
          >
            <Picker.Item label="Viewer" value="VIEWER" />
            <Picker.Item label="Operator" value="OPERATOR" />
            <Picker.Item label="Farm Admin" value="FARM_ADMIN" />
            <Picker.Item label="Super Admin" value="SUPERADMIN" />
          </Picker>
        </View>

        <TouchableOpacity
          style={styles.button}
          onPress={() => handleApprove(item.id)}
        >
          <Text style={styles.buttonText}>Aprovar</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#10b981" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {pendingUsers.length === 0 ? (
        <Text style={styles.emptyText}>Nenhuma conta aguardando aprovação.</Text>
      ) : (
        <FlatList
          data={pendingUsers}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={{ paddingBottom: 20 }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a', padding: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f172a' },
  emptyText: { color: '#94a3b8', textAlign: 'center', marginTop: 40 },
  card: { backgroundColor: '#1e293b', padding: 16, borderRadius: 8, marginBottom: 12, borderWidth: 1, borderColor: '#334155' },
  emailText: { color: '#10b981', fontSize: 16, fontWeight: 'bold', marginBottom: 4 },
  idText: { color: '#f8fafc', fontSize: 14, fontFamily: 'monospace', marginBottom: 2 },
  dateText: { color: '#94a3b8', fontSize: 14, marginBottom: 16 },
  actionRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  pickerContainer: { flex: 1, backgroundColor: '#0f172a', borderRadius: 4, marginRight: 10, overflow: 'hidden' },
  picker: { color: '#f8fafc', height: 50 },
  button: { backgroundColor: '#10b981', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 6 },
  buttonText: { color: '#ffffff', fontWeight: 'bold' }
});
