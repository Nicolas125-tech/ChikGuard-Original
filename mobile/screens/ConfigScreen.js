import React, { useState } from 'react';
import { 
  StyleSheet, Text, View, TextInput, TouchableOpacity, Alert 
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Save, LogOut } from 'lucide-react-native';

export const normalizeServerUrl = (value) => {
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

export default function ConfigScreen({ serverUrl, setServerUrl, logout }) {
  const [tempUrl, setTempUrl] = useState(serverUrl);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    const normalized = normalizeServerUrl(tempUrl);
    if (!normalized) {
      Alert.alert("URL inválido", "Use um endereço válido, exemplo: https://abc.trycloudflare.com");
      return;
    }
    setSaving(true);
    try {
      await AsyncStorage.setItem('cg_server_url', normalized);
      setServerUrl(normalized);
      setTempUrl(normalized);
      Alert.alert("Sucesso", "Endereço atualizado!");
    } catch (e) {
      Alert.alert("Erro", "Não foi possível salvar as configurações.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.pageTitle}>Ajustes do Sistema</Text>
      
      <Text style={styles.label}>Endereço do Servidor (Cloudflare Tunnel ou IP)</Text>
      <TextInput 
        style={styles.input} 
        value={tempUrl} 
        onChangeText={setTempUrl} 
        placeholder="https://exemplo.trycloudflare.com" 
        placeholderTextColor="#64748b"
        autoCapitalize='none'
        autoCorrect={false}
      />
      
      <TouchableOpacity style={styles.btnPrimary} onPress={save} disabled={saving}>
        <Save color="#fff" size={20} />
        <Text style={styles.btnText}>{saving ? "Salvando..." : "Salvar Endereço"}</Text>
      </TouchableOpacity>

      <View style={styles.logoutContainer}>
        <TouchableOpacity style={styles.btnLogout} onPress={logout}>
          <LogOut color="#ef4444" size={20} />
          <Text style={styles.logoutText}>Sair da Conta</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a', padding: 20 },
  pageTitle: { fontSize: 22, fontWeight: 'bold', color: 'white', marginBottom: 20, marginTop: 10 },
  label: { color: '#94a3b8', marginBottom: 10, fontSize: 12, fontWeight: 'bold' },
  input: { 
    backgroundColor: '#1e293b', 
    color: 'white', 
    padding: 15, 
    borderRadius: 12, 
    marginBottom: 20, 
    borderWidth: 1, 
    borderColor: '#334155' 
  },
  btnPrimary: { 
    backgroundColor: '#10b981', 
    width: '100%', 
    padding: 18, 
    borderRadius: 16, 
    alignItems: 'center', 
    flexDirection: 'row', 
    justifyContent: 'center', 
    gap: 10 
  },
  btnText: { color: 'white', fontWeight: 'bold', fontSize: 16 },
  logoutContainer: { 
    marginTop: 40, 
    borderTopWidth: 1, 
    borderTopColor: '#334155', 
    paddingTop: 20 
  },
  btnLogout: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    padding: 15, 
    backgroundColor: '#1e293b', 
    borderRadius: 12, 
    justifyContent: 'center' 
  },
  logoutText: { color: '#ef4444', fontWeight: 'bold', marginLeft: 10 }
});
