import React, { useState, useEffect, useCallback } from 'react';
import { Cpu, Wind, Zap, SlidersHorizontal, Radio, Activity } from 'lucide-react';
import { getBaseUrl } from '../utils/config';
import { toast } from 'sonner';

export default function IoTBridgePanel({ token, serverIP }) {
  const [iotStatus, setIotStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCode, setShowCode] = useState(false);
  const baseUrl = getBaseUrl(serverIP);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/api/iot/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIotStatus(data);
      }
    } catch (err) {
      console.error("Erro ao buscar status do IoT Bridge:", err);
    } finally {
      setLoading(false);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000); // Polling a cada 3s para o painel de debug
    return () => clearInterval(interval);
  }, [fetchStatus]);

  if (loading) return null;

  const isConnected = iotStatus?.mqtt_connected;
  
  // Extrai apenas o IP do broker (remove a porta se existir para simplificar pro arduino)
  const mqttServerHost = iotStatus?.broker ? iotStatus.broker.split(':')[0] : serverIP || '192.168.1.xxx';
  const mqttTopic = iotStatus?.topic ? iotStatus.topic.replace('+', 'farm-1') : 'chikguard/farm/farm-1/sensors';

  const arduinoCode = `#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

const char* ssid = "NOME_DO_SEU_WIFI";
const char* password = "SENHA_DO_WIFI";
const char* mqtt_server = "${mqttServerHost}"; // IP do Servidor ChikGuard Edge

WiFiClient espClient;
PubSubClient client(espClient);

#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\\nWiFi conectado!");
  
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    while (!client.connected()) {
      if (client.connect("ESP32_ChikGuard_Node1")) {
        Serial.println("MQTT Conectado!");
      } else {
        delay(5000);
      }
    }
  }
  client.loop();

  // Leitura dos sensores (simulada ou real)
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  float amonia = 12.5; // Substitua pelo pino analógico do sensor MQ137
  
  if (!isnan(temp)) {
    // Formata o JSON exigido pelo ChikGuard
    String payload = "{\\"temperature_c\\":" + String(temp) + 
                     ",\\"humidity_pct\\":" + String(hum) + 
                     ",\\"ammonia_ppm\\":" + String(amonia) + "}";
                     
    client.publish("${mqttTopic}", payload.c_str());
    Serial.println("Enviado: " + payload);
  }
  
  delay(10000); // Envia a cada 10 segundos
}`;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-sm mt-6 mb-6">
      <div className="flex items-center gap-3 mb-6">
        <div className={`p-2.5 rounded-xl border ${isConnected ? 'bg-emerald-500/20 border-emerald-500/30' : 'bg-rose-500/20 border-rose-500/30'}`}>
          <Radio size={24} className={isConnected ? "text-emerald-400" : "text-rose-400"} />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Ponte IoT MQTT (Sensores Locais)</h2>
          <p className="text-xs text-slate-400 mt-1">Conexão direta com ESP32/Arduinos via Mosquitto</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-950/50 p-4 rounded-2xl border border-slate-800/80">
          <div className="text-slate-400 text-xs font-semibold mb-1">Status do Broker</div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></div>
            <span className="text-white font-bold">{isConnected ? 'CONECTADO' : 'DESCONECTADO'}</span>
          </div>
          <div className="text-slate-500 text-xs mt-1 truncate">{iotStatus?.broker || 'N/A'}</div>
        </div>

        <div className="bg-slate-950/50 p-4 rounded-2xl border border-slate-800/80">
           <div className="text-slate-400 text-xs font-semibold mb-1">Tópico Assinado</div>
           <div className="text-white font-mono text-sm break-all">{iotStatus?.topic || 'N/A'}</div>
           <div className="text-slate-500 text-xs mt-1">
             Fonte Atual: <span className="text-indigo-300 font-medium">{iotStatus?.current_sensor_source}</span>
           </div>
        </div>

        <div className="bg-slate-950/50 p-4 rounded-2xl border border-slate-800/80 flex flex-col justify-center">
           <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-xs font-semibold">Mensagens Recebidas</span>
              <Activity size={14} className="text-indigo-400" />
           </div>
           <div className="text-2xl font-bold text-white mb-1">
             {iotStatus?.messages_received || 0}
           </div>
           <div className="text-slate-500 text-xs">
             Última leitura: {iotStatus?.last_message_at ? new Date(iotStatus.last_message_at * 1000).toLocaleTimeString('pt-BR') : 'Nunca'}
           </div>
        </div>
      </div>

      {/* Arduino Code Generator Section */}
      <div className="mt-6 border-t border-slate-800 pt-6">
        <button 
          onClick={() => setShowCode(!showCode)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold py-2 px-4 rounded-xl transition-colors flex items-center gap-2 mb-4"
        >
          <Cpu size={16} />
          {showCode ? 'Ocultar Código C++ (ESP32/Arduino)' : 'Conectar novo Arduino/ESP32'}
        </button>

        {showCode && (
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-hidden relative group">
            <button 
               onClick={() => {
                 navigator.clipboard.writeText(arduinoCode);
                 toast.success('Código copiado para a área de transferência!');
               }}
               className="absolute top-4 right-4 bg-slate-800 hover:bg-slate-700 text-slate-300 p-2 rounded-lg text-xs font-semibold opacity-0 group-hover:opacity-100 transition-opacity"
            >
               Copiar Código
            </button>
            <div className="text-emerald-400 text-xs font-mono mb-2">/* Firmware para ESP32 - ChikGuard IoT Node */</div>
            <pre className="text-slate-300 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
              {arduinoCode}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
