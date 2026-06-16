import logging
import threading
from typing import Any, Dict, List, Optional

import numpy as np

from src.core.cv_engine import CameraCapture

logger = logging.getLogger("chikguard.multicamera")


class MultiCameraOrchestrator:
    """
    Orquestrador de múltiplos streams de vídeo em paralelo (Roteador RTSP).
    Inicia e gerencia threads CameraCapture isoladas para evitar que lentidões
    de conexões individuais travem o loop de exibição geral.
    """

    def __init__(self, target_fps: float = 15.0, width: int = 1280, height: int = 720):
        self.target_fps = target_fps
        self.width = width
        self.height = height

        # Estrutura de canais ativos: camera_id -> CameraCapture
        self._streams: Dict[str, CameraCapture] = {}
        self._lock = threading.Lock()

    def add_stream(self, camera_id: str, source: Any, backend: int = 0) -> bool:
        """Instancia, inicia e registra um novo canal de stream de vídeo de forma thread-safe."""
        with self._lock:
            if camera_id in self._streams:
                logger.warning(
                    f"[MultiCamera] Conexão ignorada. A câmera {camera_id} já está ativa."
                )
                return False

            try:
                capture = CameraCapture(
                    camera_index=source,
                    target_fps=self.target_fps,
                    width=self.width,
                    height=self.height,
                    backend=backend,
                )
                capture.start()
                self._streams[camera_id] = capture
                logger.info(
                    f"[MultiCamera] Canal '{camera_id}' iniciado com sucesso a partir de: {source}"
                )
                return True
            except Exception as exc:
                logger.exception(
                    f"[MultiCamera] Erro crítico ao iniciar canal '{camera_id}': {exc}"
                )
                return False

    def remove_stream(self, camera_id: str) -> bool:
        """Encerra e remove o canal de stream ativo informado."""
        with self._lock:
            capture = self._streams.pop(camera_id, None)
            if not capture:
                return False

            try:
                capture.stop()
                logger.info(f"[MultiCamera] Canal '{camera_id}' parado e liberado com sucesso.")
                return True
            except Exception as exc:
                logger.error(
                    f"[MultiCamera] Falha ao desalocar recursos do canal '{camera_id}': {exc}"
                )
                return False

    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Recupera sem bloqueio o frame mais recente do buffer LIFO da câmera informada."""
        capture = self._streams.get(camera_id)
        if not capture:
            return None
        return capture.latest_frame(timeout=0.01)

    def list_active_streams(self) -> List[str]:
        """Retorna uma lista com os IDs de todas as câmeras ativas."""
        with self._lock:
            return list(self._streams.keys())

    def stop_all(self):
        """Encerra todas as capturas ativas e esvazia a fila de conexões gerenciadas."""
        with self._lock:
            for camera_id, capture in list(self._streams.items()):
                try:
                    capture.stop()
                    logger.info(f"[MultiCamera] Canal '{camera_id}' encerrado na liberação global.")
                except Exception as exc:
                    logger.error(
                        f"[MultiCamera] Erro ao encerrar canal '{camera_id}' na parada global: {exc}"
                    )
            self._streams.clear()
