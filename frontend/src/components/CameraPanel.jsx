import React, { useState } from 'react';
import { Maximize, WifiOff } from 'lucide-react';
import WebRTCVideo from './WebRTCVideo';
import HeatmapOverlay from './HeatmapOverlay';
import { getBaseUrl } from '../utils/config';

export default function CameraPanel({ token, serverIP }) {
  const [videoBlocked, setVideoBlocked] = useState(false);
  const [showHeatmapOverlay, setShowHeatmapOverlay] = useState(false);
  
  const baseUrl = getBaseUrl(serverIP);
  const webrtcUrl = `${baseUrl}/api/webrtc/offer`;

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col gap-4">
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-3xl overflow-hidden h-full relative flex flex-col shadow-sm backdrop-blur-sm">
        <div className="p-4 border-b border-slate-800/80 flex flex-row justify-between items-center bg-slate-950/80 backdrop-blur-md absolute top-0 left-0 right-0 z-20">
          <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm uppercase tracking-wider">
            <Maximize size={16} className="text-emerald-400" /> Câmera Principal
          </h3>
          <button 
            onClick={() => setShowHeatmapOverlay(v => !v)}
            className="text-xs font-semibold bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 rounded-lg px-3 py-1.5 transition-colors"
          >
            {showHeatmapOverlay ? 'Ocultar Heatmap' : 'Mostrar Heatmap AI'}
          </button>
        </div>

        <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden h-full">
          {videoBlocked ? (
            <div className="text-center flex flex-col items-center justify-center h-full w-full bg-slate-950/50 absolute inset-0">
              <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 flex flex-col items-center">
                <WifiOff size={40} className="text-slate-600 mb-4" />
                <p className="text-slate-400 font-medium">Aguardando Conexão com Câmera Real</p>
                <p className="text-slate-500 text-xs mt-2">Sem simuladores disponíveis</p>
              </div>
            </div>
          ) : (
            <>
              <WebRTCVideo 
                url={webrtcUrl} 
                token={token} 
                className="absolute inset-0 w-full h-full object-contain z-0" 
                onConnectionStateChange={(state) => { 
                  if(state === 'failed' || state === 'disconnected' || state === 'closed') { 
                    setVideoBlocked(true); 
                  } 
                }} 
              />
              {showHeatmapOverlay && <HeatmapOverlay serverIP={serverIP} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
