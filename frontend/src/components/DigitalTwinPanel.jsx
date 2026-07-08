import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Layers, Thermometer, Bird, Cpu, AlertTriangle, Fan, Flame, Activity } from 'lucide-react';
import { getBaseUrl } from '../utils/config';
import DigitalTwin3D from './DigitalTwin3D';
import { isDeepEqual } from '../utils/performance';

export default function DigitalTwinPanel({ token, serverIP, cameras = [], activeCamera }) {
  const [activeLayer, setActiveLayer] = useState('sensors'); // 'sensors' | 'birds' | 'devices' | 'alerts'
  const [sensorLive, setSensorLive] = useState(null);
  const [deviceState, setDeviceState] = useState({ ventilacao: false, aquecedor: false });
  const [heatmapPoints, setHeatmapPoints] = useState([]);
  const [thermalAnomalies, setThermalAnomalies] = useState([]);
  const [loading, setLoading] = useState(false);

  const baseUrl = getBaseUrl(serverIP);
  const farmName = cameras.find(c => c.camera_id === activeCamera)?.name || 'Galpão Principal 1';

  // ── Fetching Data ──
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [rSensors, rDevices, rHeatmap, rAnomalies] = await Promise.all([
        fetch(`${baseUrl}/api/sensors/live`, { headers }),
        fetch(`${baseUrl}/api/estado-dispositivos`, { headers }),
        fetch(`${baseUrl}/api/heatmap/3d?hours=1&grid=24`, { headers }),
        fetch(`${baseUrl}/api/thermal-anomalies/live?minutes=15`, { headers }),
      ]);

      // Bolt Optimization: Prevent unnecessary re-renders when polling data is identical.
      if (rSensors.ok) {
        const sData = await rSensors.json();
        setSensorLive(prev => isDeepEqual(prev, sData) ? prev : sData);
      }

      if (rDevices.ok) {
        const dData = await rDevices.json();
        setDeviceState(prev => isDeepEqual(prev, dData) ? prev : dData);
      }

      if (rHeatmap.ok) {
        const hData = await rHeatmap.json();
        const newPoints = hData.points || [];
        setHeatmapPoints(prev => isDeepEqual(prev, newPoints) ? prev : newPoints);
      }

      if (rAnomalies.ok) {
        const aData = await rAnomalies.json();
        const newItems = aData.items || [];
        setThermalAnomalies(prev => isDeepEqual(prev, newItems) ? prev : newItems);
      }
    } catch (err) {
      console.error('Error fetching digital twin data:', err);
    } finally {
      setLoading(false);
    }
  }, [baseUrl, token]);

  useEffect(() => {
    setTimeout(() => fetchData(), 0);
    const interval = setInterval(fetchData, 6000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // ── Temperature Interpolation ──
  const temp = sensorLive?.temperature_c ?? 0.0;

  const virtualSensors = useMemo(() => {
    return [
      { id: 1, name: 'Sensor Entrada Ar (A1)', x: 0.15, y: 0.25, temp: temp },
      { id: 2, name: 'Sensor Central Superior (A3)', x: 0.85, y: 0.25, temp: temp },
      { id: 3, name: 'Sensor Central Médio (B2)', x: 0.50, y: 0.50, temp: temp },
      { id: 4, name: 'Sensor Exaustor Lateral (C1)', x: 0.15, y: 0.75, temp: temp },
      { id: 5, name: 'Sensor Central Inferior (C3)', x: 0.85, y: 0.75, temp: temp },
      { id: 6, name: 'Sensor Lateral Médio (B3)', x: 0.85, y: 0.50, temp: temp },
    ];
  }, [temp]);

  // Color mapping function for temperature
  const getTempColor = (t) => {
    if (t < 20) return 'rgba(59, 130, 246, 0.45)'; // Blue/Cold
    if (t <= 26) return 'rgba(16, 185, 129, 0.45)'; // Emerald/Optimal
    if (t <= 30) return 'rgba(245, 158, 11, 0.45)'; // Amber/Warm
    return 'rgba(239, 68, 68, 0.45)'; // Red/Hot
  };

  // Calculate sector density and check for crowding
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


  // Bolt Optimization: Pre-calculate thermal anomalies by sector in an O(N) pass
  // using useMemo, replacing the O(N * 9) filter inside the render loop.
  const anomaliesBySector = useMemo(() => {
    const bySector = {
      A1: 0, A2: 0, A3: 0,
      B1: 0, B2: 0, B3: 0,
      C1: 0, C2: 0, C3: 0,
    };
    thermalAnomalies.forEach(a => {
      let sec = a.sector;
      if (!sec && a.x && a.y) {
        let col = a.x < 213 ? 1 : a.x < 426 ? 2 : 3;
        let row = a.y < 160 ? 'A' : a.y < 320 ? 'B' : 'C';
        sec = `${row}${col}`;
      }
      if (sec && bySector[sec] !== undefined) {
        bySector[sec] += 1;
      }
    });
    return bySector;
  }, [thermalAnomalies]);

  const isVentActive = deviceState.ventilacao;
  const isHeatActive = deviceState.aquecedor;

  return (
    <div className="space-y-6">
      {/* ── View Selectors ── */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 bg-slate-900/60 border border-slate-800 rounded-2xl w-fit">
        <button
          aria-pressed={activeLayer === 'sensors'}
          onClick={() => setActiveLayer('sensors')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl transition-all duration-200 ${
            activeLayer === 'sensors'
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 shadow-md shadow-emerald-500/5'
              : 'text-slate-400 hover:text-slate-200 border border-transparent'
          }`}
        >
          <Thermometer size={14} aria-hidden="true" /><span>Mapa Térmico</span>
        </button>
        <button
          aria-pressed={activeLayer === 'birds'}
          onClick={() => setActiveLayer('birds')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl transition-all duration-200 ${
            activeLayer === 'birds'
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 shadow-md shadow-emerald-500/5'
              : 'text-slate-400 hover:text-slate-200 border border-transparent'
          }`}
        >
          <Bird size={14} aria-hidden="true" /><span>Densidade de Aves</span>
        </button>
        <button
          aria-pressed={activeLayer === 'devices'}
          onClick={() => setActiveLayer('devices')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl transition-all duration-200 ${
            activeLayer === 'devices'
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 shadow-md shadow-emerald-500/5'
              : 'text-slate-400 hover:text-slate-200 border border-transparent'
          }`}
        >
          <Cpu size={14} aria-hidden="true" /><span>Status Equipamentos</span>
        </button>
        <button
          aria-pressed={activeLayer === 'alerts'}
          onClick={() => setActiveLayer('alerts')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl transition-all duration-200 ${
            activeLayer === 'alerts'
              ? 'bg-rose-500/15 text-rose-400 border border-rose-500/20 shadow-md shadow-rose-500/5'
              : 'text-slate-400 hover:text-slate-200 border border-transparent'
          }`}
        >
          <AlertTriangle size={14} aria-hidden="true" /><span>Alertas Clínicos ({thermalAnomalies.length})</span>
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* ── Floor Plan Display ── */}
        <div className="xl:col-span-3 p-6 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm flex flex-col justify-between min-h-[500px]">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-white font-bold text-sm uppercase tracking-wider flex items-center gap-2">
                <Layers size={16} className="text-emerald-400" /> {farmName} - Gêmeo Digital
              </h3>
              <p className="text-slate-500 text-xs mt-0.5">Visão espacial em tempo real.</p>
            </div>
            {loading && <div className="text-slate-500 text-xs animate-pulse">Atualizando...</div>}
          </div>

          {/* ── Schematic Layout (Barn Map) ── */}
          <div className="relative border border-slate-800 rounded-3xl bg-slate-950 aspect-[21/9] w-full overflow-hidden shadow-inner p-2">
            
            {/* Grid Sectors (A1 to C3) */}
            <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 pointer-events-none">
              {['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3'].map((sec) => (
                <div
                  key={sec}
                  className="border border-slate-800/40 relative flex items-center justify-center"
                >
                  <span className="text-[10px] font-bold text-slate-700 absolute top-2 left-2 uppercase tracking-wide">
                    {sec}
                  </span>
                  {activeLayer === 'birds' && sectorDensities[sec] > 80 && (
                    <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[9px] font-bold px-1.5 py-0.5 rounded absolute bottom-2 right-2 animate-pulse">
                      CROWDING CRÍTICO
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* LAYER 1: Temperature Heatmap Interpolation */}
            {activeLayer === 'sensors' && (
              <div className="absolute inset-0 pointer-events-none" style={{ mixBlendMode: 'screen' }}>
                {virtualSensors.map((s) => {
                  const blobColor = getTempColor(s.temp);
                  return (
                    <div
                      key={s.id}
                      className="absolute rounded-full"
                      style={{
                        left: `${s.x * 100}%`,
                        top: `${s.y * 100}%`,
                        width: '35%',
                        height: '75%',
                        transform: 'translate(-50%, -50%)',
                        background: `radial-gradient(circle, ${blobColor} 0%, rgba(0,0,0,0) 70%)`,
                        filter: 'blur(20px)',
                      }}
                    />
                  );
                })}
              </div>
            )}

            {/* LAYER 2: Bird Crowding Tracking Cloud */}
            {activeLayer === 'birds' && (
              <div className="absolute inset-0 pointer-events-none" style={{ mixBlendMode: 'screen' }}>
                {heatmapPoints.map((pt, i) => {
                  const intensity = pt.heat_intensity || 0;
                  if (intensity < 0.05) return null;

                  const colorStops = intensity > 0.6
                    ? `rgba(239, 68, 68, ${intensity * 0.85}) 0%, rgba(239, 68, 68, 0) 70%` // Red
                    : intensity > 0.3
                    ? `rgba(245, 158, 11, ${intensity * 0.85}) 0%, rgba(245, 158, 11, 0) 70%` // Amber
                    : `rgba(16, 185, 129, ${intensity * 0.85}) 0%, rgba(16, 185, 129, 0) 70%`; // Emerald

                  const size = 12 + (intensity * 18);

                  return (
                    <div
                      key={i}
                      className="absolute rounded-full"
                      style={{
                        left: `${pt.x * 100}%`,
                        top: `${pt.y * 100}%`,
                        width: `${size}%`,
                        height: `${size * 2.3}%`,
                        transform: 'translate(-50%, -50%)',
                        background: `radial-gradient(circle, ${colorStops})`,
                        filter: 'blur(6px)',
                      }}
                    />
                  );
                })}
              </div>
            )}

            {/* LAYER 3: Active Equipment Layer */}
            {activeLayer === 'devices' && (
              <>
                {/* Exhaust Fans (Left Wall) */}
                <div className="absolute left-2 top-0 bottom-0 flex flex-col justify-around z-10">
                  {[1, 2, 3].map((fId) => (
                    <div
                      key={fId}
                      className={`p-1.5 rounded-xl border flex items-center justify-center bg-slate-900 transition-all ${
                        isVentActive
                          ? 'border-blue-500/50 text-blue-400 shadow-md shadow-blue-500/10'
                          : 'border-slate-800 text-slate-600'
                      }`}
                    >
                      <Fan
                        size={20}
                        className={isVentActive ? 'animate-spin' : ''}
                        style={{ animationDuration: isVentActive ? '0.8s' : '0s' }}
                      />
                    </div>
                  ))}
                </div>

                {/* Heaters (Right Ceiling Area) */}
                <div className="absolute right-8 top-0 bottom-0 flex flex-col justify-around z-10">
                  {[1, 2].map((hId) => (
                    <div
                      key={hId}
                      className={`p-1.5 rounded-xl border flex items-center justify-center bg-slate-900 transition-all ${
                        isHeatActive
                          ? 'border-orange-500/50 text-orange-400 shadow-md shadow-orange-500/10 animate-pulse'
                          : 'border-slate-800 text-slate-600'
                      }`}
                    >
                      <Flame size={20} />
                    </div>
                  ))}
                </div>

                {/* Visual Airflow Vectors */}
                {isVentActive && (
                  <div className="absolute inset-0 pointer-events-none flex items-center overflow-hidden">
                    <div className="w-full h-1/2 flex flex-col justify-around text-blue-500/25 select-none font-mono text-sm leading-none tracking-widest pl-20 pr-20 animate-pulse">
                      <div className="animate-slide-left">« « « « « « « « « « « « « « « « « « «</div>
                      <div className="animate-slide-left" style={{ animationDelay: '0.4s' }}>« « « « « « « « « « « « « « « « « « «</div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* LAYER 4: Clinical Anomalies Overlays */}
            {activeLayer === 'alerts' && (
              <div className="absolute inset-0 pointer-events-none z-20">
                {thermalAnomalies.map((anom) => {
                  // Normalize coordinates if needed, or place them in their estimated sector
                  // Let's estimate coordinate based on sector if x/y are missing or zero
                  let xPct = 0.5;
                  let yPct = 0.5;

                  if (anom.x && anom.y) {
                    // Frame is typically 640x480. Let's scale to percent.
                    xPct = Math.min(1.0, Math.max(0.0, anom.x / 640.0));
                    yPct = Math.min(1.0, Math.max(0.0, anom.y / 480.0));
                  } else if (anom.sector) {
                    const rowLetter = anom.sector.charAt(0);
                    const colNum = parseInt(anom.sector.charAt(1)) || 2;
                    yPct = rowLetter === 'A' ? 0.20 : rowLetter === 'B' ? 0.50 : 0.80;
                    xPct = colNum === 1 ? 0.16 : colNum === 2 ? 0.50 : 0.84;
                  }

                  const isFever = anom.kind === 'fever_suspected';

                  return (
                    <div
                      key={anom.id}
                      className="absolute group pointer-events-auto"
                      style={{
                        left: `${xPct * 100}%`,
                        top: `${yPct * 100}%`,
                        transform: 'translate(-50%, -50%)',
                      }}
                    >
                      <div className={`relative flex items-center justify-center w-8 h-8 rounded-full border animate-pulse ${
                        isFever
                          ? 'bg-rose-500/20 border-rose-500 text-rose-400'
                          : 'bg-blue-500/20 border-blue-500 text-blue-400'
                      }`}>
                        <AlertTriangle size={15} />
                      </div>
                      
                      {/* Tooltip on hover */}
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-slate-950 border border-slate-800 p-2.5 rounded-xl text-[10px] text-slate-300 w-48 shadow-xl pointer-events-none z-30">
                        <p className="font-bold text-white uppercase">{isFever ? 'Febre Suspeita' : 'Hipotermia/Morte'}</p>
                        <p className="text-slate-400 mt-0.5">Ave UID: <span className="font-mono font-semibold text-slate-200">#{anom.bird_uid || 'N/A'}</span></p>
                        <p className="text-slate-400">Temp: <span className="font-semibold text-white">{anom.estimated_temp_c}°C</span></p>
                        <p className="text-[9px] text-slate-500 mt-1">{anom.timestamp}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Static Sensor Placements Visual Icons */}
            {virtualSensors.map((s) => (
              <div
                key={s.id}
                className="absolute flex items-center justify-center pointer-events-auto group cursor-help z-10"
                style={{
                  left: `${s.x * 100}%`,
                  top: `${s.y * 100}%`,
                  transform: 'translate(-50%, -50%)',
                }}
              >
                <div className="bg-slate-900 border border-slate-800/80 hover:border-slate-600 rounded-full w-5 h-5 flex items-center justify-center text-[8px] font-bold text-slate-400 shadow-md">
                  T
                </div>
                <div className="absolute left-full ml-1.5 hidden group-hover:flex items-center bg-slate-900/95 border border-slate-800 px-2.5 py-1.5 rounded-lg text-[9px] text-slate-300 w-40 pointer-events-none shadow-lg z-30">
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-200">{s.name}</span>
                    <span className="font-semibold text-emerald-400 mt-0.5">{s.temp.toFixed(1)} °C</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* ── Status Footer Summary ── */}
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-950/40 border border-slate-800/50 p-4 rounded-2xl">
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Média Térmica</span>
              <span className="text-lg font-extrabold text-white mt-1">
                {temp.toFixed(1)} <span className="text-xs text-slate-500 font-medium">°C</span>
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Aves Monitoradas</span>
              <span className="text-lg font-extrabold text-emerald-400 mt-1 flex items-center gap-1.5">
                <Bird size={16} /> {heatmapPoints.length}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Exaustores</span>
              <span className={`text-sm font-bold mt-2 flex items-center gap-1.5 ${isVentActive ? 'text-blue-400' : 'text-slate-600'}`}>
                <Fan size={14} className={isVentActive ? 'animate-spin' : ''} />
                {isVentActive ? 'Ativo' : 'Desligado'}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Aquecedores</span>
              <span className={`text-sm font-bold mt-2 flex items-center gap-1.5 ${isHeatActive ? 'text-orange-400' : 'text-slate-600'}`}>
                <Flame size={14} />
                {isHeatActive ? 'Lotes Ativos' : 'Desligado'}
              </span>
            </div>
          </div>
        </div>

        {/* ── Side Insights Panel ── */}
        <div className="space-y-6">
          {/* Spatial Temperature Grid */}
          <div className="p-5 rounded-3xl border border-slate-700/50 bg-slate-900/80 shadow-sm backdrop-blur-sm">
            <h4 className="text-slate-400 text-xs font-bold uppercase tracking-widest flex items-center gap-2 mb-4">
              <Activity size={14} className="text-emerald-400" /> Detalhes dos Setores
            </h4>
            <div className="space-y-3.5 max-h-[400px] overflow-y-auto pr-1">
              {['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3'].map((sec) => {
                const birdCount = sectorDensities[sec];
                const alertsCount = anomaliesBySector[sec] || 0;

                let secTemp = temp;

                return (
                  <div key={sec} className="bg-slate-950/50 border border-slate-800/80 p-3 rounded-xl flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-xs font-bold text-slate-300">
                        {sec}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] text-slate-500 font-bold uppercase">Aves</span>
                        <span className="text-xs font-bold text-white">{birdCount} detecções</span>
                      </div>
                    </div>
                    
                    <div className="flex flex-col items-end">
                      <span className="text-xs font-bold text-slate-300">{secTemp.toFixed(1)}°C</span>
                      {alertsCount > 0 ? (
                        <span className="text-[8px] bg-rose-500/10 text-rose-400 font-semibold px-1 rounded border border-rose-500/20 mt-0.5 animate-pulse">
                          {alertsCount} Alertas
                        </span>
                      ) : (
                        <span className="text-[8px] text-slate-500 mt-0.5">Estável</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 3D WEBGL VERSION */}
      {activeLayer === 'sensors' && (
        <DigitalTwin3D sensors={sensorLive} devices={deviceState} birds={heatmapPoints} />
      )}
    </div>
  );
}
