import React, { useState } from 'react';
import { Maximize, WifiOff, Layers, RefreshCw } from 'lucide-react';
import WebRTCVideo from './WebRTCVideo';
import HeatmapOverlay from './HeatmapOverlay';
import { getBaseUrl } from '../utils/config';

export default function CameraPanel({ token, serverIP, cameras = [], activeCamera }) {
  const [videoBlocked, setVideoBlocked] = useState(false);
  const [showHeatmapOverlay, setShowHeatmapOverlay] = useState(false);
  const [useWebRTC, setUseWebRTC] = useState(true);
  
  const baseUrl = getBaseUrl(serverIP);
  const webrtcUrl = `${baseUrl}/api/webrtc/offer`;
  const mjpegUrl = token ? `${baseUrl}/api/video?token=${token}` : `${baseUrl}/api/video`;
  const farmName = cameras.find(c => c.camera_id === activeCamera)?.name || 'Câmera Principal';

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col gap-4">
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-3xl overflow-hidden h-full relative flex flex-col shadow-sm backdrop-blur-sm">
        <div className="p-4 border-b border-slate-800/80 flex flex-row justify-between items-center bg-slate-950/80 backdrop-blur-md absolute top-0 left-0 right-0 z-20">
          <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm uppercase tracking-wider">
            <Maximize size={16} className="text-emerald-400" /> {farmName}
          </h3>
          <button 
            onClick={() => setShowHeatmapOverlay(v => !v)}
            aria-pressed={showHeatmapOverlay}
            className="flex items-center gap-1.5 text-xs font-semibold bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 rounded-lg px-3 py-1.5 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 focus:outline-none"
          >
            <Layers size={14} aria-hidden="true" className={showHeatmapOverlay ? "text-emerald-400" : "text-slate-400"} />
            {showHeatmapOverlay ? 'Ocultar Heatmap' : 'Mostrar Heatmap AI'}
          </button>
        </div>

        <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden h-full">
          {videoBlocked ? (
            <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-950/50 absolute inset-0 z-10">
              <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 flex flex-col items-center">
                <WifiOff size={40} className="text-slate-600 mb-4" />
                <p className="text-slate-400 font-medium">Aguardando Conexão com Câmera Real</p>
                <p className="text-slate-500 text-xs mt-2">Sem simuladores disponíveis</p>
                <button 
                  onClick={() => { setVideoBlocked(false); setUseWebRTC(true); }}
                  className="mt-4 flex items-center gap-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"
                >
                  <RefreshCw size={14} aria-hidden="true" />
                  Tentar Novamente
                </button>
              </div>
            </div>
          ) : useWebRTC ? (
            <>
              <WebRTCVideo 
                url={webrtcUrl} 
                token={token}
                className="absolute inset-0 w-full h-full object-contain z-0" 
                onConnectionStateChange={(state) => { 
                  if(state === 'failed' || state === 'disconnected' || state === 'closed') { 
                    console.warn("WebRTC failed, falling back to MJPEG stream");
                    setUseWebRTC(false); 
                  } 
                }} 
              />
              {showHeatmapOverlay && <HeatmapOverlay serverIP={serverIP} token={token} />}
            </>
          ) : (
            <>
              <img 
                src={mjpegUrl} 
                alt="Live Camera Feed"
                className="absolute inset-0 w-full h-full object-contain z-0"
                onError={() => setVideoBlocked(true)}
              />
              {showHeatmapOverlay && <HeatmapOverlay serverIP={serverIP} token={token} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
