import threading
import time
import logging
import random
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from database import db, AcousticReading, EventLog, Batch

logger = logging.getLogger("chikguard.audio")

class ContinuousAudioMonitor:
    """
    Monitor de Bioacústica Contínua em Tempo Real.
    Roda em segundo plano capturando o áudio ambiente, analisando estresse/tosse e disparando alarmes.
    """
    def __init__(self, classifier, app_context_fn, interval_seconds: float = 10.0):
        self.classifier = classifier
        self.app_context_fn = app_context_fn
        self.interval_seconds = interval_seconds
        
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia a execução da thread do monitoramento contínuo."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="chikguard-audio-monitor")
        self._thread.start()
        logger.info("[AudioMonitor] Thread de bioacústica contínua iniciada.")

    def stop(self):
        """Para a execução do monitoramento de áudio."""
        self._running = False

    def _generate_mock_audio(self) -> Tuple[np.ndarray, int]:
        """Gera um buffer de áudio simulado de 16kHz com ruídos e espirros eventuais do lote."""
        sample_rate = 16000
        # Simulação de ruído de fundo da ventilação do galpão
        audio_buffer = np.random.normal(0, 0.01, sample_rate)
        
        # Simula esporadicamente tosse (10% de probabilidade)
        if random.random() < 0.1:
            time_space = np.linspace(0, 1, sample_rate)
            cough_signature = np.sin(2 * np.pi * 400 * time_space) * np.exp(-10 * time_space)
            audio_buffer += cough_signature * 0.5
            
        return audio_buffer, sample_rate

    # ── Métodos de Processamento e Persistência (SRP) ──

    def _log_critical_acoustic_event(self, cough_idx: float, stress_idx: float):
        """Registra logs de auditoria e alertas caso os thresholds respiratórios sejam violados."""
        if cough_idx <= 50.0 and stress_idx <= 60.0:
            return

        active_batch = Batch.query.filter(Batch.active == True).first()
        batch_id = active_batch.id if active_batch else None
        
        severity_level = "high" if cough_idx > 70.0 else "warning"
        
        event = EventLog(
            camera_id="galpao-1",
            event_type="acoustic_alert",
            level=severity_level,
            message=f"Pico acústico detectado: Tosse={cough_idx:.1f}%, Estresse={stress_idx:.1f}%",
            metadata_json=f'{{"cough_index": {cough_idx}, "stress_index": {stress_idx}, "batch_id": {batch_id}}}'
        )
        db.session.add(event)

    def _process_audio_frame(self, audio_data: np.ndarray, sample_rate: int):
        """Classifica o espectro de frequências e salva a telemetria acústica no banco."""
        classification = self.classifier.classify(audio_data, sample_rate)
        if not classification:
            return

        resp_health = classification["respiratory_health_index"]
        cough_idx = classification["cough_index"]
        stress_idx = classification["stress_audio_index"]
        
        # Converte percentual em escala de float 0.0 - 1.0 para o banco
        reading = AcousticReading(
            camera_id="galpao-1",
            respiratory_health_index=resp_health / 100.0,
            cough_index=cough_idx / 100.0,
            stress_audio_index=stress_idx / 100.0,
            source="continuous_monitor"
        )
        db.session.add(reading)
        
        self._log_critical_acoustic_event(cough_idx, stress_idx)
        db.session.commit()
        logger.debug(f"[AudioMonitor] Telemetria acústica salva: Tosse={cough_idx:.1f}%, Resp={resp_health:.1f}%")

    def _run(self):
        """Loop de monitoramento executado de forma assíncrona na thread."""
        while self._running:
            try:
                audio_data, sample_rate = self._generate_mock_audio()
                with self.app_context_fn():
                    self._process_audio_frame(audio_data, sample_rate)
            except Exception as exc:
                logger.error(f"[AudioMonitor] Erro inesperado na thread de áudio: {exc}")
                
            time.sleep(self.interval_seconds)
