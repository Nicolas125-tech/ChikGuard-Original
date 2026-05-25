import threading
import logging
from typing import Dict, Any, List, Optional
import numpy as np
from src.core.cv_engine import CameraCapture

logger = logging.getLogger("chikguard.multicamera")

class MultiCameraOrchestrator:
    """Orquestrador de múltiplas câmeras / fluxos RTSP (Roteador de Vídeo).

    Gerencia o ciclo de vida de múltiplos streams de vídeo em paralelo,
    garantindo que cada câmera rode em sua própria thread assíncrona
    para evitar gargalos de latência.
    """
    def __init__(self, target_fps: float = 15.0, width: int = 1280, height: int = 720):
        self.target_fps = target_fps
        self.width = width
        self.height = height
        
        # Dicionário de capturadores ativos indexado por camera_id
        self._streams: Dict[str, CameraCapture] = {}
        self._lock = threading.Lock()

    def add_stream(self, camera_id: str, source: Any, backend: int = 0) -> bool:
        """Adiciona e inicia um novo fluxo de câmera.

        Args:
            camera_id: ID único da câmera/galpão (ex: 'galpao-1').
            source: Índice da câmera (int) ou URL RTSP (str) / caminho de vídeo.
            backend: Backend OpenCV de captura (ex: cv2.CAP_DSHOW ou cv2.CAP_ANY).
        """
        with self._lock:
            if camera_id in self._streams:
                logger.warning("[MultiCamera] Câmera %s já está ativa. Ignorando.", camera_id)
                return False

            try:
                # Instancia o capturador assíncrono para o fluxo específico
                capture = CameraCapture(
                    camera_index=source,
                    target_fps=self.target_fps,
                    width=self.width,
                    height=self.height,
                    backend=backend
                )
                capture.start()
                self._streams[camera_id] = capture
                logger.info("[MultiCamera] Fluxo '%s' adicionado com sucesso a partir da origem: %s", camera_id, source)
                return True
            except Exception as e:
                logger.exception("[MultiCamera] Falha ao iniciar fluxo '%s': %s", camera_id, e)
                return False

    def remove_stream(self, camera_id: str) -> bool:
        """Para e remove um fluxo de câmera ativo."""
        with self._lock:
            if camera_id not in self._streams:
                return False

            try:
                capture = self._streams.pop(camera_id)
                capture.stop()
                logger.info("[MultiCamera] Fluxo '%s' parado e removido.", camera_id)
                return True
            except Exception as e:
                logger.error("[MultiCamera] Erro ao parar fluxo '%s': %s", camera_id, e)
                return False

    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Retorna o frame mais recente de uma câmera específica sem bloqueio."""
        capture = self._streams.get(camera_id)
        if capture:
            # Retorna o frame mais recente do buffer LIFO
            return capture.latest_frame(timeout=0.01)
        return None

    def list_active_streams(self) -> List[str]:
        """Retorna a lista de IDs de todas as câmeras atualmente ativas."""
        with self._lock:
            return list(self._streams.keys())

    def stop_all(self):
        """Para e libera todos os fluxos de vídeo gerenciados."""
        with self._lock:
            for camera_id, capture in list(self._streams.items()):
                try:
                    capture.stop()
                    logger.info("[MultiCamera] Fluxo '%s' parado durante encerramento global.", camera_id)
                except Exception as e:
                    logger.error("[MultiCamera] Erro ao parar fluxo '%s': %s", camera_id, e)
            self._streams.clear()
