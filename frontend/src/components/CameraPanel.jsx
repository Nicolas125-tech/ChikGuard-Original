import React, { useState, useEffect, useRef } from 'react';
import { Maximize, WifiOff, Layers, RefreshCw, Camera, Video, AlertCircle } from 'lucide-react';
import WebRTCVideo from './WebRTCVideo';
import HeatmapOverlay from './HeatmapOverlay';
import { getBaseUrl } from '../utils/config';
import { toast } from 'sonner';

export default function CameraPanel({ token, serverIP, cameras = [], activeCamera }) {
  const [videoBlocked, setVideoBlocked] = useState(false);
  const [showHeatmapOverlay, setShowHeatmapOverlay] = useState(false);
  const [useWebRTC, setUseWebRTC] = useState(true);
  
  // Local Webcam State
  const [source, setSource] = useState('server'); // 'server' or 'local'
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [localStream, setLocalStream] = useState(null);
  const [cameraPermission, setCameraPermission] = useState('prompt'); // 'prompt', 'granted', 'denied'
  const localVideoRef = useRef(null);

  const baseUrl = getBaseUrl(serverIP);
  const webrtcUrl = `${baseUrl}/api/webrtc/offer`;
  const mjpegUrl = token ? `${baseUrl}/api/video?token=${token}` : `${baseUrl}/api/video`;
  const farmName = cameras.find(c => c.camera_id === activeCamera)?.name || 'Câmera Principal';

  // Request camera permission and enumerate devices
  const initLocalCamera = async () => {
    try {
      setCameraPermission('prompt');
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      
      // Stop the temp stream immediately, we will start it with the chosen deviceId
      stream.getTracks().forEach(track => track.stop());
      
      setCameraPermission('granted');
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = allDevices.filter(d => d.kind === 'videoinput');
      setDevices(videoDevices);
      
      if (videoDevices.length > 0) {
        setSelectedDeviceId(prev => prev || videoDevices[0].deviceId);
      }
    } catch (err) {
      console.error('Permission denied or error getting media:', err);
      setCameraPermission('denied');
      toast.error('Permissão de câmera negada ou erro ao iniciar.');
    }
  };

  // Start stream with selected device ID
  const startStream = async (deviceId) => {
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
    }
    
    try {
      const constraints = {
        video: deviceId ? { deviceId: { exact: deviceId } } : true
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      setLocalStream(stream);
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error('Error starting video stream:', err);
      toast.error('Erro ao iniciar transmissão do dispositivo selecionado.');
    }
  };

  // Trigger stream start when device or source changes
  useEffect(() => {
    if (source === 'local' && cameraPermission === 'granted' && selectedDeviceId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      startStream(selectedDeviceId);
    } else {
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        setLocalStream(null);
      }
    }
    return () => {
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [source, selectedDeviceId, cameraPermission]);

  const handleDeviceChange = (e) => {
    setSelectedDeviceId(e.target.value);
  };

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col gap-4">
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-3xl overflow-hidden h-full relative flex flex-col shadow-sm backdrop-blur-sm">
        <div className="p-4 border-b border-slate-800/80 flex flex-row justify-between items-center bg-slate-950/80 backdrop-blur-md absolute top-0 left-0 right-0 z-20 gap-2 flex-wrap">
          <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm uppercase tracking-wider">
            <Maximize size={16} className="text-emerald-400" /> {farmName}
          </h3>
          
          <div className="flex items-center gap-2">
            {/* Segmented Control for Source Selection */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-0.5 flex gap-1 text-xs">
              <button 
                onClick={() => setSource('server')}
                className={`px-3 py-1.5 rounded-md font-semibold transition-all ${source === 'server' ? 'bg-emerald-500 text-white shadow shadow-emerald-500/25' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Transmissão da Granja
              </button>
              <button 
                onClick={() => {
                  setSource('local');
                  if (cameraPermission !== 'granted') {
                    initLocalCamera();
                  }
                }}
                className={`px-3 py-1.5 rounded-md font-semibold transition-all flex items-center gap-1 ${source === 'local' ? 'bg-emerald-500 text-white shadow shadow-emerald-500/25' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Camera size={13} />
                Câmera Local
              </button>
            </div>

            <button 
              onClick={() => setShowHeatmapOverlay(v => !v)}
              aria-pressed={showHeatmapOverlay}
              className="flex items-center gap-1.5 text-xs font-semibold bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 rounded-lg px-3 py-1.5 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 focus:outline-none"
            >
              <Layers size={14} aria-hidden="true" className={showHeatmapOverlay ? "text-emerald-400" : "text-slate-400"} />
              {showHeatmapOverlay ? 'Ocultar Heatmap' : 'Mostrar Heatmap AI'}
            </button>
          </div>
        </div>

        <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden h-full">
          {source === 'local' ? (
            /* Local Camera View */
            <div className="absolute inset-0 w-full h-full flex flex-col items-center justify-center bg-slate-950">
              {cameraPermission === 'prompt' && (
                <div className="bg-slate-900 border border-slate-800 p-8 rounded-3xl text-center max-w-sm flex flex-col items-center shadow-2xl">
                  <Video size={48} className="text-emerald-400 mb-4 animate-pulse" />
                  <h4 className="text-lg font-bold text-white mb-2">Permissão de Câmera Requerida</h4>
                  <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                    Para visualizar a câmera USB local ou webcam no sistema, autorize o acesso no seu navegador.
                  </p>
                  <button 
                    onClick={initLocalCamera}
                    className="bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-emerald-500/25 flex items-center gap-2"
                  >
                    <Camera size={16} />
                    Autorizar e Iniciar
                  </button>
                </div>
              )}

              {cameraPermission === 'denied' && (
                <div className="bg-slate-900 border border-slate-800 p-8 rounded-3xl text-center max-w-sm flex flex-col items-center shadow-2xl">
                  <AlertCircle size={48} className="text-rose-500 mb-4" />
                  <h4 className="text-lg font-bold text-white mb-2">Acesso Negado</h4>
                  <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                    O acesso à câmera local foi bloqueado. Por favor, redefina as permissões do site na barra de endereços do seu navegador e clique no botão abaixo.
                  </p>
                  <button 
                    onClick={initLocalCamera}
                    className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-6 py-2.5 rounded-xl font-bold transition-all"
                  >
                    Tentar Novamente
                  </button>
                </div>
              )}

              {cameraPermission === 'granted' && (
                <>
                  <video 
                    ref={localVideoRef} 
                    className="absolute inset-0 w-full h-full object-contain z-0" 
                    autoPlay 
                    playsInline 
                    muted 
                  />
                  {showHeatmapOverlay && <HeatmapOverlay serverIP={serverIP} token={token} />}
                  
                  {/* Local Camera Device Selector Overlay */}
                  <div className="absolute bottom-4 left-4 right-4 bg-slate-950/80 backdrop-blur-md border border-slate-800 p-3 rounded-2xl z-10 flex items-center justify-between gap-4 max-w-md mx-auto">
                    <div className="flex items-center gap-2 min-w-0">
                      <Camera size={16} className="text-emerald-400 shrink-0" />
                      <span className="text-xs font-semibold text-slate-300 truncate">Câmera ativa no dispositivo</span>
                    </div>
                    {devices.length > 1 && (
                      <select 
                        value={selectedDeviceId}
                        onChange={handleDeviceChange}
                        className="bg-slate-900 text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-medium focus:outline-none focus:border-emerald-500 cursor-pointer max-w-[200px]"
                      >
                        {devices.map(d => (
                          <option key={d.deviceId} value={d.deviceId}>{d.label || `Câmera ${d.deviceId.slice(0, 5)}`}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </>
              )}
            </div>
          ) : (
            /* Server Stream */
            videoBlocked ? (
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
            )
          )}
        </div>
      </div>
    </div>
  );
}

