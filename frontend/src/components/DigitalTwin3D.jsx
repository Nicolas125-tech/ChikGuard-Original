import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Activity, Thermometer, Wind } from 'lucide-react';

// Bolt Optimization: Memoize Fan to prevent unnecessary re-renders when DigitalTwin3D updates
const Fan = React.memo(function Fan({ position, isRunning }) {
  const meshRef = useRef();
  
  useFrame((state, delta) => {
    if (isRunning && meshRef.current) {
      meshRef.current.rotation.z += delta * 15;
    }
  });

  return (
    <group position={position} rotation={[0, Math.PI / 2, 0]}>
      <mesh>
        <cylinderGeometry args={[0.6, 0.6, 0.2, 32]} />
        <meshStandardMaterial color="#334155" metalness={0.8} roughness={0.2} />
      </mesh>
      <mesh ref={meshRef}>
        <cylinderGeometry args={[0.5, 0.5, 0.05, 4]} />
        <meshStandardMaterial color={isRunning ? "#10b981" : "#94a3b8"} metalness={0.5} roughness={0.5} />
      </mesh>
    </group>
  );
});

// Bolt Optimization: Memoize Heater to prevent unnecessary re-renders when DigitalTwin3D updates
const Heater = React.memo(function Heater({ position, isOn }) {
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[0.8, 0.4, 0.4]} />
        <meshStandardMaterial color="#1e293b" />
      </mesh>
      <mesh position={[0, 0, 0.21]}>
        <planeGeometry args={[0.7, 0.3]} />
        <meshBasicMaterial color={isOn ? "#ef4444" : "#475569"} />
      </mesh>
      {isOn && (
        <pointLight position={[0, 0, 0.5]} distance={4} intensity={1.5} color="#ef4444" />
      )}
    </group>
  );
});

// Bolt Optimization: Memoize Shed to prevent unnecessary re-renders when DigitalTwin3D updates
const Shed = React.memo(function Shed({ sensors, devices, birds, width, length }) {
  const isFanOn = devices?.ventilacao === true;
  const isHeaterOn = devices?.aquecedor === true;
  
  // Create heatmap spots based on temperature
  const temp = sensors?.temperature_c || 25;
  const heatColor = temp > 30 ? "#ef4444" : temp < 20 ? "#3b82f6" : "#f97316";

  return (
    <group>
      {/* Floor */}
      <mesh position={[0, -0.5, 0]} receiveShadow>
        <boxGeometry args={[width, 0.2, length]} />
        <meshStandardMaterial color="#78716c" roughness={0.9} />
      </mesh>
      
      {/* Walls (Transparent) */}
      <mesh position={[-width/2, 1.5, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.2, 4, length]} />
        <meshStandardMaterial color="#cbd5e1" transparent opacity={0.3} />
      </mesh>
      <mesh position={[width/2, 1.5, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.2, 4, length]} />
        <meshStandardMaterial color="#cbd5e1" transparent opacity={0.3} />
      </mesh>
      <mesh position={[0, 1.5, length/2]} castShadow receiveShadow>
        <boxGeometry args={[width, 4, 0.2]} />
        <meshStandardMaterial color="#cbd5e1" transparent opacity={0.3} />
      </mesh>
      <mesh position={[0, 1.5, -length/2]} castShadow receiveShadow>
        <boxGeometry args={[width, 4, 0.2]} />
        <meshStandardMaterial color="#cbd5e1" transparent opacity={0.3} />
      </mesh>

      {/* Roof Frame */}
      <mesh position={[0, 3.5, 0]} rotation={[0, 0, 0]}>
         <boxGeometry args={[width, 0.2, length]} />
         <meshStandardMaterial color="#334155" wireframe />
      </mesh>

      {/* Equipment */}
      {/* Exhaust fans at the back wall */}
      <Fan position={[-width/4, 1.5, -length/2 + 0.2]} isRunning={isFanOn} />
      <Fan position={[0, 1.5, -length/2 + 0.2]} isRunning={isFanOn} />
      <Fan position={[width/4, 1.5, -length/2 + 0.2]} isRunning={isFanOn} />

      {/* Heaters hanging from roof */}
      <Heater position={[-2, 2.5, -5]} isOn={isHeaterOn} />
      <Heater position={[2, 2.5, -5]} isOn={isHeaterOn} />
      <Heater position={[-2, 2.5, 5]} isOn={isHeaterOn} />
      <Heater position={[2, 2.5, 5]} isOn={isHeaterOn} />

      {/* Bird Heatmap Spots rendered dynamically from AI tracking data */}
      {birds && birds.length > 0 ? (
        birds.map((pt, i) => {
          // pt.x and pt.y are 0 to 1
          const posX = (pt.x * width) - (width / 2);
          const posZ = (pt.y * length) - (length / 2);
          return (
            <group key={i} position={[posX, -0.3, posZ]}>
              <mesh>
                <sphereGeometry args={[0.3, 16, 16]} />
                <meshStandardMaterial color="#fcd34d" emissive="#fbbf24" emissiveIntensity={0.5} roughness={0.6} />
              </mesh>
              <pointLight intensity={0.3} distance={2} color="#fcd34d" />
            </group>
          );
        })
      ) : (
        // Fallback default lights if no birds API data is present
        <>
          <pointLight position={[-2, 0.5, 2]} intensity={temp > 25 ? 1 : 0} distance={5} color={heatColor} />
          <pointLight position={[3, 0.5, -4]} intensity={temp > 25 ? 1 : 0} distance={5} color={heatColor} />
          <pointLight position={[0, 0.5, 8]} intensity={temp > 25 ? 1 : 0} distance={5} color={heatColor} />
          <pointLight position={[-3, 0.5, -8]} intensity={temp > 25 ? 1 : 0} distance={5} color={heatColor} />
        </>
      )}
      
    </group>
  );
});

export default function DigitalTwin3D({ sensors, devices, birds }) {
  const [width, setWidth] = useState(12);
  const [length, setLength] = useState(24);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-sm mt-6">
      <div className="flex flex-col sm:flex-row justify-between sm:items-start mb-6 gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-500/20 p-2.5 rounded-xl border border-indigo-500/30">
            <Activity size={24} className="text-indigo-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Gêmeo Digital 3D (WebGL)</h2>
            <p className="text-xs text-slate-400 mt-1">Simulação proporcional da granja</p>
          </div>
        </div>
        
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3 bg-slate-950 p-2 rounded-xl border border-slate-800 self-end">
             <div className={`px-3 py-1 rounded-lg text-xs font-bold flex items-center gap-1 ${devices?.ventilacao ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                <Wind size={14} /> Exaustão
             </div>
             <div className={`px-3 py-1 rounded-lg text-xs font-bold flex items-center gap-1 ${devices?.aquecedor ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800 text-slate-500'}`}>
                <Thermometer size={14} /> Aquecimento
             </div>
          </div>
          
          <div className="flex items-center gap-2 bg-slate-800/50 p-2 rounded-xl border border-slate-700/50">
             <div className="flex items-center gap-1">
               <label className="text-xs text-slate-400 font-medium ml-1">Largura (m):</label>
               <input type="number" min="5" max="30" value={width} onChange={(e)=>setWidth(Number(e.target.value))} className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-white w-14 outline-none" />
             </div>
             <div className="flex items-center gap-1">
               <label className="text-xs text-slate-400 font-medium ml-1">Comprimento (m):</label>
               <input type="number" min="10" max="60" value={length} onChange={(e)=>setLength(Number(e.target.value))} className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-white w-14 outline-none" />
             </div>
          </div>
        </div>
      </div>
      
      <div className="h-[400px] w-full rounded-2xl overflow-hidden bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-700 cursor-move relative shadow-inner">
        <Canvas shadows camera={{ position: [0, Math.max(10, length/2), Math.max(15, length)], fov: 45 }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[10, 15, 10]} intensity={1.5} castShadow shadow-mapSize={[1024, 1024]} />
          
          <Shed sensors={sensors} devices={devices} birds={birds} width={width} length={length} />
          
          <OrbitControls 
            enablePan={false} 
            maxPolarAngle={Math.PI / 2 - 0.05} 
            minDistance={5} 
            maxDistance={40} 
            autoRotate 
            autoRotateSpeed={0.5}
          />
        </Canvas>
        
        <div className="absolute bottom-4 right-4 bg-slate-900/80 backdrop-blur-md px-3 py-2 rounded-lg border border-slate-700 pointer-events-none text-xs text-slate-300">
          Arraste o mouse para girar, scroll para zoom
        </div>
        <div className="absolute top-4 left-4 bg-slate-900/80 backdrop-blur-md px-3 py-2 rounded-lg border border-slate-700 pointer-events-none text-xs font-mono text-emerald-400 flex items-center gap-2">
          <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
          AO VIVO
        </div>
      </div>
    </div>
  );
}
