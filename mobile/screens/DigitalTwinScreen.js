import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { 
  StyleSheet, Text, View, ScrollView, TouchableOpacity, 
  ActivityIndicator, Dimensions, Animated, Alert
} from 'react-native';
import Svg, { 
  Rect, Circle, Ellipse, Line, Text as SvgText, Defs, RadialGradient, Stop, G 
} from 'react-native-svg';
import { 
  Layers, Thermometer, Bird, Cpu, AlertTriangle, Wind, Zap, Activity 
} from 'lucide-react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const { width: screenWidth } = Dimensions.get('window');
const MAP_HEIGHT = 200;
const MAP_WIDTH = screenWidth - 40; // padding of 20 on each side

export default function DigitalTwinScreen({ serverUrl, token }) {
  const [activeLayer, setActiveLayer] = useState('sensors'); // 'sensors' | 'birds' | 'devices' | 'alerts'
  const [sensorLive, setSensorLive] = useState(null);
  const [deviceState, setDeviceState] = useState({ ventilacao: false, aquecedor: false });
  const [heatmapPoints, setHeatmapPoints] = useState([]);
  const [thermalAnomalies, setThermalAnomalies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedElement, setSelectedElement] = useState(null);

  // Animations
  const spinValue = useRef(new Animated.Value(0)).current;
  const pulseValue = useRef(new Animated.Value(1)).current;

  // Fetching Data
  const fetchData = useCallback(async () => {
    if (!serverUrl) return;
    setLoading(true);
    try {
      // 1. Live sensors
      const rSensors = await fetch(`${serverUrl}/api/sensors/live`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (rSensors.ok) {
        setSensorLive(await rSensors.json());
      }

      // 2. Device state
      const rDevices = await fetch(`${serverUrl}/api/estado-dispositivos`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (rDevices.ok) {
        setDeviceState(await rDevices.json());
      }

      // 3. Heatmap points
      const rHeatmap = await fetch(`${serverUrl}/api/heatmap/3d?hours=1&grid=24`);
      if (rHeatmap.ok) {
        const hData = await rHeatmap.json();
        setHeatmapPoints(hData.points || []);
      }

      // 4. Thermal anomalies
      const rAnomalies = await fetch(`${serverUrl}/api/thermal-anomalies/live?minutes=15`);
      if (rAnomalies.ok) {
        const aData = await rAnomalies.json();
        setThermalAnomalies(aData.items || []);
      }
    } catch (err) {
      console.warn('Error fetching digital twin data:', err);
    } finally {
      setLoading(false);
    }
  }, [serverUrl, token]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Handle Animations
  const isVentActive = deviceState?.ventilacao;
  const isHeatActive = deviceState?.aquecedor;

  useEffect(() => {
    if (isVentActive) {
      Animated.loop(
        Animated.timing(spinValue, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        })
      ).start();
    } else {
      spinValue.setValue(0);
    }
  }, [isVentActive]);

  useEffect(() => {
    if (isHeatActive) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseValue, {
            toValue: 0.3,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseValue, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          })
        ])
      ).start();
    } else {
      pulseValue.setValue(1);
    }
  }, [isHeatActive]);

  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg']
  });

  // Temperature Interpolation
  const temp = sensorLive?.temperature_c ?? 25.0;

  const virtualSensors = useMemo(() => {
    return [
      { id: 1, name: 'Sensor Entrada Ar (A1)', x: 0.15, y: 0.25, temp: temp - (isVentActive ? 1.8 : 0.8) },
      { id: 2, name: 'Sensor Central Superior (A3)', x: 0.85, y: 0.25, temp: temp + (isHeatActive ? 2.4 : 0.6) },
      { id: 3, name: 'Sensor Central Médio (B2)', x: 0.50, y: 0.50, temp: temp + 0.3 },
      { id: 4, name: 'Sensor Exaustor Lateral (C1)', x: 0.15, y: 0.75, temp: temp - (isVentActive ? 2.2 : 0.4) },
      { id: 5, name: 'Sensor Central Inferior (C3)', x: 0.85, y: 0.75, temp: temp + (isHeatActive ? 1.8 : 0.5) },
      { id: 6, name: 'Sensor Lateral Médio (B3)', x: 0.85, y: 0.50, temp: temp + 0.1 },
    ];
  }, [temp, isVentActive, isHeatActive]);

  const getTempColor = (t) => {
    if (t < 20) return '#3b82f6'; // Blue
    if (t <= 26) return '#10b981'; // Emerald
    if (t <= 30) return '#f59e0b'; // Amber
    return '#ef4444'; // Red
  };

  const getTempColorRgba = (t, opacity) => {
    if (t < 20) return `rgba(59, 130, 246, ${opacity})`;
    if (t <= 26) return `rgba(16, 185, 129, ${opacity})`;
    if (t <= 30) return `rgba(245, 158, 11, ${opacity})`;
    return `rgba(239, 68, 68, ${opacity})`;
  };

  // Sector density and crowding
  const sectorDensities = useMemo(() => {
    const densities = {
      A1: 0, A2: 0, A3: 0,
      B1: 0, B2: 0, B3: 0,
      C1: 0, C2: 0, C3: 0,
    };
    heatmapPoints.forEach(pt => {
      let col = pt.x < 0.33 ? 1 : pt.x < 0.66 ? 2 : 3;
      let row = pt.y < 0.33 ? 'A' : pt.y < 0.66 ? 'B' : 'C';
      densities[`${row}${col}`] += 1;
    });
    return densities;
  }, [heatmapPoints]);

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.pageTitle}>Gêmeo Digital 2D</Text>

      {/* View Selectors */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.layerSelectorScroll}>
        <View style={styles.layerSelectorContainer}>
          <TouchableOpacity
            style={[styles.layerButton, activeLayer === 'sensors' && styles.layerButtonActive]}
            onPress={() => { setActiveLayer('sensors'); setSelectedElement(null); }}
          >
            <Thermometer size={14} color={activeLayer === 'sensors' ? '#10b981' : '#94a3b8'} />
            <Text style={[styles.layerButtonText, activeLayer === 'sensors' && styles.layerButtonTextActive]}>Mapa Térmico</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.layerButton, activeLayer === 'birds' && styles.layerButtonActive]}
            onPress={() => { setActiveLayer('birds'); setSelectedElement(null); }}
          >
            <Bird size={14} color={activeLayer === 'birds' ? '#10b981' : '#94a3b8'} />
            <Text style={[styles.layerButtonText, activeLayer === 'birds' && styles.layerButtonTextActive]}>Densidade</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.layerButton, activeLayer === 'devices' && styles.layerButtonActive]}
            onPress={() => { setActiveLayer('devices'); setSelectedElement(null); }}
          >
            <Cpu size={14} color={activeLayer === 'devices' ? '#10b981' : '#94a3b8'} />
            <Text style={[styles.layerButtonText, activeLayer === 'devices' && styles.layerButtonTextActive]}>Equipamentos</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.layerButton, activeLayer === 'alerts' && activeLayer === 'alerts' ? styles.layerButtonActiveRose : styles.layerButtonActive]}
            onPress={() => { setActiveLayer('alerts'); setSelectedElement(null); }}
          >
            <AlertTriangle size={14} color={activeLayer === 'alerts' ? '#ef4444' : '#94a3b8'} />
            <Text style={[styles.layerButtonText, activeLayer === 'alerts' && styles.layerButtonTextActiveRose]}>
              Alertas ({thermalAnomalies.length})
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* SVG Canvas Map */}
      <View style={styles.mapContainer}>
        <Svg height={MAP_HEIGHT} width={MAP_WIDTH} style={styles.svgCanvas}>
          <Defs>
            {/* Radial Gradients for Sensors */}
            {virtualSensors.map(s => (
              <RadialGradient 
                key={`grad-${s.id}`} 
                id={`grad-${s.id}`} 
                cx="50%" 
                cy="50%" 
                rx="50%" 
                ry="50%"
              >
                <Stop offset="0%" stopColor={getTempColor(s.temp)} stopOpacity="0.6" />
                <Stop offset="100%" stopColor={getTempColor(s.temp)} stopOpacity="0" />
              </RadialGradient>
            ))}
          </Defs>

          {/* Background and Border */}
          <Rect x={0} y={0} width={MAP_WIDTH} height={MAP_HEIGHT} fill="#020617" rx={16} stroke="#1e293b" strokeWidth={1} />

          {/* Grid Sectors Layout (A1-C3) */}
          <G stroke="#1e293b" strokeWidth={0.5} strokeDasharray="4,4">
            {/* Columns */}
            <Line x1={MAP_WIDTH / 3} y1={0} x2={MAP_WIDTH / 3} y2={MAP_HEIGHT} />
            <Line x1={(2 * MAP_WIDTH) / 3} y1={0} x2={(2 * MAP_WIDTH) / 3} y2={MAP_HEIGHT} />
            {/* Rows */}
            <Line x1={0} y1={MAP_HEIGHT / 3} x2={MAP_WIDTH} y2={MAP_HEIGHT / 3} />
            <Line x1={0} y1={(2 * MAP_HEIGHT) / 3} x2={MAP_WIDTH} y2={(2 * MAP_HEIGHT) / 3} />
          </G>

          {/* Sector Labels */}
          {['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3'].map((sec, idx) => {
            const col = idx % 3;
            const row = Math.floor(idx / 3);
            const x = (col * MAP_WIDTH / 3) + 12;
            const y = (row * MAP_HEIGHT / 3) + 18;
            return (
              <SvgText key={sec} x={x} y={y} fill="#475569" fontSize="10" fontWeight="bold">
                {sec}
              </SvgText>
            );
          })}

          {/* Layer 1: Sensor Thermal Maps */}
          {activeLayer === 'sensors' && (
            virtualSensors.map(s => {
              const xPos = s.x * MAP_WIDTH;
              const yPos = s.y * MAP_HEIGHT;
              return (
                <Ellipse
                  key={`heat-${s.id}`}
                  cx={xPos}
                  cy={yPos}
                  rx={MAP_WIDTH * 0.22}
                  ry={MAP_HEIGHT * 0.35}
                  fill={`url(#grad-${s.id})`}
                />
              );
            })
          )}

          {/* Layer 2: Bird Densities Cloud */}
          {activeLayer === 'birds' && (
            heatmapPoints.map((pt, i) => {
              const intensity = pt.heat_intensity || 0;
              if (intensity < 0.05) return null;
              const xPos = pt.x * MAP_WIDTH;
              const yPos = pt.y * MAP_HEIGHT;
              const size = 6 + (intensity * 12);
              const color = intensity > 0.6 ? 'rgba(239, 68, 68, 0.7)' : intensity > 0.3 ? 'rgba(245, 158, 11, 0.7)' : 'rgba(16, 185, 129, 0.7)';
              return (
                <Circle
                  key={`bird-pt-${i}`}
                  cx={xPos}
                  cy={yPos}
                  r={size}
                  fill={color}
                />
              );
            })
          )}

          {/* Layer 3: Active Equipment Indicators */}
          {activeLayer === 'devices' && (
            <G>
              {/* Fan Placements (Left Wall) */}
              {[0.16, 0.5, 0.84].map((yFrac, idx) => {
                const xPos = 18;
                const yPos = yFrac * MAP_HEIGHT;
                return (
                  <Circle
                    key={`fan-${idx}`}
                    cx={xPos}
                    cy={yPos}
                    r={12}
                    fill="#0f172a"
                    stroke={isVentActive ? '#3b82f6' : '#334155'}
                    strokeWidth={1.5}
                  />
                );
              })}
              {/* Heater Placements (Right Wall) */}
              {[0.25, 0.75].map((yFrac, idx) => {
                const xPos = MAP_WIDTH - 18;
                const yPos = yFrac * MAP_HEIGHT;
                return (
                  <Circle
                    key={`heat-${idx}`}
                    cx={xPos}
                    cy={yPos}
                    r={12}
                    fill="#0f172a"
                    stroke={isHeatActive ? '#f97316' : '#334155'}
                    strokeWidth={1.5}
                  />
                );
              })}
            </G>
          )}

          {/* Layer 4: Clinical Alerts (Anomalies) */}
          {activeLayer === 'alerts' && (
            thermalAnomalies.map((anom) => {
              let xPct = 0.5;
              let yPct = 0.5;
              if (anom.x && anom.y) {
                xPct = Math.min(1.0, Math.max(0.0, anom.x / 640.0));
                yPct = Math.min(1.0, Math.max(0.0, anom.y / 480.0));
              } else if (anom.sector) {
                const rowLetter = anom.sector.charAt(0);
                const colNum = parseInt(anom.sector.charAt(1)) || 2;
                yPct = rowLetter === 'A' ? 0.20 : rowLetter === 'B' ? 0.50 : 0.80;
                xPct = colNum === 1 ? 0.16 : colNum === 2 ? 0.50 : 0.84;
              }
              const xPos = xPct * MAP_WIDTH;
              const yPos = yPct * MAP_HEIGHT;
              const isFever = anom.kind === 'fever_suspected';

              return (
                <G key={anom.id} onPress={() => setSelectedElement({ type: 'anomaly', data: anom })}>
                  <Circle
                    cx={xPos}
                    cy={yPos}
                    r={10}
                    fill={isFever ? 'rgba(239, 68, 68, 0.3)' : 'rgba(59, 130, 246, 0.3)'}
                    stroke={isFever ? '#ef4444' : '#3b82f6'}
                    strokeWidth={1.5}
                  />
                </G>
              );
            })
          )}

          {/* Interactive Sensor Nodes */}
          {virtualSensors.map(s => {
            const xPos = s.x * MAP_WIDTH;
            const yPos = s.y * MAP_HEIGHT;
            return (
              <G key={`node-${s.id}`} onPress={() => setSelectedElement({ type: 'sensor', data: s })}>
                <Circle cx={xPos} cy={yPos} r={6} fill="#1e293b" stroke="#64748b" strokeWidth={1} />
              </G>
            );
          })}
        </Svg>

        {/* Animated Overlays on top of the Map */}
        {activeLayer === 'devices' && (
          <View style={StyleSheet.absoluteFill} pointerEvents="none">
            {/* Animated Fans */}
            {[0.16, 0.5, 0.84].map((yFrac, idx) => (
              <Animated.View
                key={`fan-rot-${idx}`}
                style={{
                  position: 'absolute',
                  left: 6,
                  top: yFrac * MAP_HEIGHT - 12,
                  width: 24,
                  height: 24,
                  alignItems: 'center',
                  justifyContent: 'center',
                  transform: [{ rotate: spin }]
                }}
              >
                <Wind size={14} color={isVentActive ? '#3b82f6' : '#64748b'} />
              </Animated.View>
            ))}

            {/* Animated Heaters */}
            {[0.25, 0.75].map((yFrac, idx) => (
              <Animated.View
                key={`heat-pls-${idx}`}
                style={{
                  position: 'absolute',
                  right: 6,
                  top: yFrac * MAP_HEIGHT - 12,
                  width: 24,
                  height: 24,
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: pulseValue
                }}
              >
                <Zap size={14} color={isHeatActive ? '#f97316' : '#64748b'} />
              </Animated.View>
            ))}
          </View>
        )}
      </View>

      {/* Selected Element Tooltip Drawer */}
      {selectedElement && (
        <View style={styles.tooltipCard}>
          <View style={styles.tooltipHeader}>
            <Text style={styles.tooltipTitle}>
              {selectedElement.type === 'sensor' ? 'Leitura de Sensor' : 'Alerta Clínico Detectado'}
            </Text>
            <TouchableOpacity onPress={() => setSelectedElement(null)} style={styles.tooltipClose}>
              <Text style={{ color: '#94a3b8', fontWeight: 'bold' }}>X</Text>
            </TouchableOpacity>
          </View>

          {selectedElement.type === 'sensor' ? (
            <View>
              <Text style={styles.tooltipLabel}>{selectedElement.data.name}</Text>
              <Text style={[styles.tooltipValue, { color: getTempColor(selectedElement.data.temp) }]}>
                {selectedElement.data.temp.toFixed(1)}°C
              </Text>
            </View>
          ) : (
            <View>
              <Text style={styles.tooltipLabel}>
                Ave UID: <Text style={styles.tooltipHighlight}>#{selectedElement.data.bird_uid || 'N/A'}</Text>
              </Text>
              <Text style={styles.tooltipLabel}>
                Sintoma: <Text style={styles.tooltipHighlight}>
                  {selectedElement.data.kind === 'fever_suspected' ? 'Febre Suspeita' : 'Hipotermia/Apática'}
                </Text>
              </Text>
              <Text style={styles.tooltipLabel}>
                Temperatura: <Text style={styles.tooltipHighlight}>{selectedElement.data.estimated_temp_c}°C</Text>
              </Text>
              <Text style={styles.tooltipDate}>{selectedElement.data.timestamp}</Text>
            </View>
          )}
        </View>
      )}

      {/* Floor Plan Footer Summary */}
      <View style={styles.summaryFooter}>
        <View style={styles.summaryCol}>
          <Text style={styles.summaryLabel}>Média Térmica</Text>
          <Text style={styles.summaryValue}>{temp.toFixed(1)}°C</Text>
        </View>
        <View style={styles.summaryCol}>
          <Text style={styles.summaryLabel}>Densidade Total</Text>
          <Text style={[styles.summaryValue, { color: '#10b981' }]}>{heatmapPoints.length} aves</Text>
        </View>
        <View style={styles.summaryCol}>
          <Text style={styles.summaryLabel}>Ventilação</Text>
          <Text style={[styles.summaryStatus, { color: isVentActive ? '#3b82f6' : '#64748b' }]}>
            {isVentActive ? 'Ativa' : 'Inativa'}
          </Text>
        </View>
        <View style={styles.summaryCol}>
          <Text style={styles.summaryLabel}>Aquecedores</Text>
          <Text style={[styles.summaryStatus, { color: isHeatActive ? '#f97316' : '#64748b' }]}>
            {isHeatActive ? 'Ativos' : 'Inativos'}
          </Text>
        </View>
      </View>

      {/* Sectors Details List */}
      <Text style={styles.sectionTitle}>Status dos Setores</Text>
      <View style={styles.sectorsCard}>
        {['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3'].map((sec) => {
          const birdCount = sectorDensities[sec] || 0;
          const alertsInSec = thermalAnomalies.filter(a => {
            if (a.sector === sec) return true;
            if (a.x && a.y) {
              let col = a.x < 213 ? 1 : a.x < 426 ? 2 : 3;
              let row = a.y < 160 ? 'A' : a.y < 320 ? 'B' : 'C';
              return `${row}${col}` === sec;
            }
            return false;
          });

          let secTemp = temp;
          if (sec.startsWith('A')) secTemp = temp - 0.4;
          if (sec.startsWith('C')) secTemp = temp + 0.5;
          if (sec.endsWith('1')) secTemp -= (isVentActive ? 1.5 : 0.4);
          if (sec.endsWith('3')) secTemp += (isHeatActive ? 2.0 : 0.6);

          return (
            <View key={sec} style={styles.sectorRow}>
              <View style={styles.sectorRowLeft}>
                <View style={styles.sectorBadge}>
                  <Text style={styles.sectorBadgeText}>{sec}</Text>
                </View>
                <View>
                  <Text style={styles.sectorName}>Setor {sec}</Text>
                  <Text style={styles.sectorMeta}>{birdCount} aves vistas</Text>
                </View>
              </View>

              <View style={styles.sectorRowRight}>
                <Text style={styles.sectorTemp}>{secTemp.toFixed(1)}°C</Text>
                {alertsInSec.length > 0 ? (
                  <View style={styles.sectorAlertBadge}>
                    <Text style={styles.sectorAlertText}>{alertsInSec.length} Alerta{alertsInSec.length > 1 ? 's' : ''}</Text>
                  </View>
                ) : (
                  <Text style={styles.sectorStableText}>Estável</Text>
                )}
              </View>
            </View>
          );
        })}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollContent: { padding: 20, paddingBottom: 40, backgroundColor: '#0f172a' },
  pageTitle: { fontSize: 22, fontWeight: 'bold', color: 'white', marginBottom: 20, marginTop: 10 },
  layerSelectorScroll: { marginBottom: 20 },
  layerSelectorContainer: { flexDirection: 'row', gap: 8 },
  layerButton: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 6, 
    paddingHorizontal: 12, 
    paddingVertical: 8, 
    borderRadius: 12, 
    borderWidth: 1, 
    borderColor: '#1e293b', 
    backgroundColor: '#1e293b' 
  },
  layerButtonActive: { borderColor: 'rgba(16, 185, 129, 0.4)', backgroundColor: 'rgba(16, 185, 129, 0.15)' },
  layerButtonActiveRose: { borderColor: 'rgba(239, 68, 68, 0.4)', backgroundColor: 'rgba(239, 68, 68, 0.15)' },
  layerButtonText: { color: '#94a3b8', fontSize: 12, fontWeight: 'bold' },
  layerButtonTextActive: { color: '#34d399' },
  layerButtonTextActiveRose: { color: '#fca5a5' },
  
  mapContainer: { 
    borderRadius: 16, 
    overflow: 'hidden', 
    position: 'relative', 
    height: MAP_HEIGHT,
    marginBottom: 20 
  },
  svgCanvas: { backgroundColor: '#020617' },
  
  tooltipCard: { 
    backgroundColor: '#020617', 
    borderColor: '#1e293b', 
    borderWidth: 1, 
    borderRadius: 16, 
    padding: 16, 
    marginBottom: 20 
  },
  tooltipHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  tooltipTitle: { color: 'white', fontWeight: 'bold', fontSize: 14 },
  tooltipClose: { padding: 4 },
  tooltipLabel: { color: '#94a3b8', fontSize: 12, marginVertical: 2 },
  tooltipHighlight: { color: 'white', fontWeight: 'bold' },
  tooltipValue: { fontSize: 24, fontWeight: 'bold', marginVertical: 4 },
  tooltipDate: { color: '#64748b', fontSize: 10, marginTop: 4 },

  summaryFooter: { 
    flexDirection: 'row', 
    backgroundColor: 'rgba(2, 6, 23, 0.4)', 
    borderColor: '#1e293b', 
    borderWidth: 1, 
    borderRadius: 16, 
    padding: 14,
    marginBottom: 25 
  },
  summaryCol: { flex: 1, alignItems: 'center' },
  summaryLabel: { color: '#64748b', fontSize: 10, fontWeight: 'bold', textTransform: 'uppercase' },
  summaryValue: { color: 'white', fontSize: 16, fontWeight: 'bold', marginTop: 4 },
  summaryStatus: { fontSize: 14, fontWeight: 'bold', marginTop: 6 },

  sectionTitle: { color: '#94a3b8', fontSize: 12, fontWeight: 'bold', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  sectorsCard: { backgroundColor: '#1e293b', borderColor: '#334155', borderWidth: 1, borderRadius: 16, overflow: 'hidden' },
  sectorRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    padding: 14, 
    borderBottomColor: '#334155', 
    borderBottomWidth: 1 
  },
  sectorRowLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  sectorBadge: { 
    width: 32, 
    height: 32, 
    borderRadius: 8, 
    backgroundColor: '#0f172a', 
    borderWidth: 1, 
    borderColor: '#334155', 
    alignItems: 'center', 
    justifyContent: 'center' 
  },
  sectorBadgeText: { color: '#94a3b8', fontSize: 12, fontWeight: 'bold' },
  sectorName: { color: 'white', fontWeight: 'bold', fontSize: 13 },
  sectorMeta: { color: '#94a3b8', fontSize: 11, marginTop: 1 },
  sectorRowRight: { alignItems: 'end' },
  sectorTemp: { color: 'white', fontWeight: 'bold', fontSize: 14, textAlign: 'right' },
  sectorStableText: { color: '#64748b', fontSize: 10, marginTop: 2, textAlign: 'right' },
  sectorAlertBadge: { 
    backgroundColor: 'rgba(239, 68, 68, 0.15)', 
    borderColor: 'rgba(239, 68, 68, 0.3)', 
    borderWidth: 1, 
    borderRadius: 4, 
    paddingHorizontal: 6, 
    paddingVertical: 2, 
    marginTop: 2 
  },
  sectorAlertText: { color: '#fca5a5', fontSize: 9, fontWeight: 'bold' }
});
