"""
ChikGuard -- AsyncCameraReader v2
==================================
Leitura de camera em thread dedicada com buffer atomico LIFO.
A thread de inferencia sempre pega o frame MAIS RECENTE,
sem nenhum bloqueio de fila ou acumulo de frames obsoletos.

Padrao: Producer-Consumer com atomic swap (lock-free no caminho critico).

Uso:
    cam = AsyncCameraReader(index=0)
    cam.start()
    frame = cam.read()   # sempre retorna o frame mais novo ou None
    cam.stop()
"""

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("chikguard.camera")


class AsyncCameraReader:
    """
    Thread de captura de camera com buffer LIFO de 1 slot.

    - A thread interna le frames da camera continuamente ao maximo de FPS.
    - O consumidor chama .read() e recebe SEMPRE o frame mais recente.
    - Sem fila: o frame antigo e substituido atomicamente (sem acumulo).
    - Reconexao automatica em caso de perda de sinal.
    """

    def __init__(
        self,
        index: int = 0,
        width: int = 1280,
        height: int = 720,
        target_fps: float = 60.0,
        backend: int = cv2.CAP_DSHOW,
        reconnect_interval_sec: float = 3.0,
        max_fail_streak: int = 30,
    ):
        self.index = index
        self.width = width
        self.height = height
        self.target_fps = max(1.0, target_fps)
        self.backend = backend
        self.reconnect_interval = reconnect_interval_sec
        self.max_fail_streak = max_fail_streak

        # --- Buffer atomico LIFO (1 slot) ------------------------------------
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()  # protege apenas a troca do slot

        # --- Controle de thread ----------------------------------------------
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_live = False  # False = sem camera real
        self._fail_streak = 0
        self._last_reconnect = 0.0

    # -------------------------------------------------------------------------
    # API publica
    # -------------------------------------------------------------------------

    @property
    def is_live(self) -> bool:
        """True se ha uma camera real aberta e lendo frames."""
        return self._is_live

    def start(self) -> "AsyncCameraReader":
        """Inicia a thread de captura. Encadeavel: cam.start()."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="chikguard-cam-reader",
        )
        self._thread.start()
        logger.info(
            "[Camera] Thread iniciada: index=%d res=%dx%d target=%.0f FPS",
            self.index,
            self.width,
            self.height,
            self.target_fps,
        )
        return self

    def stop(self):
        """Para a thread de captura e libera a camera."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
        logger.info("[Camera] Thread parada.")

    def read(self) -> Optional[np.ndarray]:
        """
        Retorna o frame mais recente ou None se ainda nao ha frame.
        Operacao de leitura O(1) — apenas uma troca de ponteiro.
        """
        with self._lock:
            return self._frame

    # -------------------------------------------------------------------------
    # Loop interno
    # -------------------------------------------------------------------------

    def _open_camera(self) -> bool:
        """Tenta abrir a camera com o backend configurado."""
        backends = [self.backend, cv2.CAP_ANY] if self.backend != cv2.CAP_ANY else [cv2.CAP_ANY]
        for b in backends:
            try:
                cap = cv2.VideoCapture(self.index, b)
                if not cap.isOpened():
                    cap.release()
                    continue

                # Configuracoes de alto desempenho
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # LIFO na camera
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

                # Verifica leitura real
                ok, test = cap.read()
                if not ok or test is None:
                    cap.release()
                    continue

                if self._cap:
                    self._cap.release()
                self._cap = cap
                self._is_live = True
                self._fail_streak = 0

                bname = {cv2.CAP_DSHOW: "DSHOW", cv2.CAP_MSMF: "MSMF"}.get(b, "ANY")
                actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = cap.get(cv2.CAP_PROP_FPS)
                logger.info(
                    "[Camera] Aberta (%s) %dx%d @ %.0f FPS (pedido: %.0f FPS)",
                    bname,
                    actual_w,
                    actual_h,
                    actual_fps,
                    self.target_fps,
                )
                return True
            except Exception as exc:
                logger.warning("[Camera] Backend %d falhou: %s", b, exc)

        logger.error("[Camera] Nenhum backend conseguiu abrir a camera %d.", self.index)
        return False

    def _run(self):
        """Loop principal da thread de captura."""
        min_interval = 1.0 / self.target_fps

        if not self._open_camera():
            self._is_live = False

        while self._running:
            t0 = time.perf_counter()

            # Sem camera: aguarda e tenta reconectar periodicamente
            if not self._is_live or self._cap is None:
                now = time.perf_counter()
                if now - self._last_reconnect > self.reconnect_interval:
                    self._last_reconnect = now
                    if self._open_camera():
                        continue
                time.sleep(0.05)
                continue

            ok, frame = self._cap.read()

            if not ok or frame is None:
                self._fail_streak += 1
                if self._fail_streak >= self.max_fail_streak:
                    logger.warning(
                        "[Camera] Sinal perdido apos %d falhas — aguardando reconexao.",
                        self._fail_streak,
                    )
                    self._is_live = False
                time.sleep(0.01)
                continue

            self._fail_streak = 0

            # Swap atomico LIFO: substitui o frame anterior sem esperar
            with self._lock:
                self._frame = frame

            # Throttle para nao consumir 100% de CPU (mas sem cap de FPS real)
            elapsed = time.perf_counter() - t0
            sleep_t = min_interval - elapsed
            if sleep_t > 0.0005:
                time.sleep(sleep_t)


class SimulatedCameraReader(AsyncCameraReader):
    """
    Camera simulada que le de um arquivo de video em loop.
    Mesma API do AsyncCameraReader -- drop-in replacement para testes.
    """

    def __init__(self, video_path: str, fps: float = 25.0):
        # Nao chama super().__init__ — backend diferente
        self._video_path = video_path
        self.target_fps = max(1.0, fps)
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._is_live = False  # Simulada = nao e "live"

    def start(self) -> "SimulatedCameraReader":
        self._running = True
        self._thread = threading.Thread(
            target=self._run_sim,
            daemon=True,
            name="chikguard-sim-reader",
        )
        self._thread.start()
        logger.info("[Camera] Simulada: %s @ %.0f FPS", self._video_path, self.target_fps)
        return self

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_sim(self):
        cap = cv2.VideoCapture(self._video_path)
        if not cap.isOpened():
            logger.error("[SimCamera] Nao foi possivel abrir: %s", self._video_path)
            return

        interval = 1.0 / self.target_fps
        while self._running:
            t0 = time.perf_counter()
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

            with self._lock:
                self._frame = frame

            elapsed = time.perf_counter() - t0
            sleep_t = interval - elapsed
            if sleep_t > 0.0005:
                time.sleep(sleep_t)

        cap.release()
