import threading
import time
import logging
import numpy as np
from datetime import datetime
from database import db, AcousticReading, EventLog, Batch

logger = logging.getLogger("chikguard.audio")

class ContinuousAudioMonitor:
    """Monitor de Bioacústica Contínua em Tempo Real.

    Roda em uma thread em segundo plano, monitorando o áudio ambiente do aviário,
    extraindo descritores acústicos e salvando leituras de estresse/tosse.
    """
    def __init__(self, classifier, app_context_fn, interval_seconds: float = 10.0):
        """
        Args:
            classifier: Instância de RespiratoryAudioClassifier.
            app_context_fn: Função que retorna o contexto de aplicação Flask (para queries do banco).
            interval_seconds: Intervalo em segundos para análise de cada bloco de som.
        """
        self.classifier = classifier
        self.app_context_fn = app_context_fn
        self.interval_seconds = interval_seconds
        
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia a thread de monitoramento contínuo de áudio."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="chikguard-audio-monitor")
        self._thread.start()
        logger.info("[AudioMonitor] Thread de bioacústica contínua iniciada.")

    def stop(self):
        """Para o monitoramento contínuo."""
        self._running = False

    def _generate_mock_audio(self) -> Tuple[np.ndarray, int]:
        """Gera um buffer de áudio simulado (16kHz, 1 segundo)."""
        sr = 16000
        # Simula ruído branco comum do aviário
        y = np.random.normal(0, 0.01, sr)
        
        # Ocasionalmente simula um surto de tosse no lote para testes (10% de chance)
        import random
        if random.random() < 0.1:
            # Sobrepõe frequências que mimetizam tosse/vocalização de estresse
            t = np.linspace(0, 1, sr)
            cough_wave = np.sin(2 * np.pi * 400 * t) * np.exp(-10 * t)
            y += cough_wave * 0.5
            
        return y, sr

    def _run(self):
        while self._running:
            try:
                # 1. Captura o buffer de áudio (Mockado para portabilidade do edge, estruturado para microfone)
                y, sr = self._generate_mock_audio()
                
                # 2. Executa a classificação usando o classificador de áudio
                # Usamos o app_context para transações seguras de banco de dados do Flask
                with self.app_context_fn():
                    result = self.classifier.classify(y, sr)
                    
                    if result:
                        resp_health = result["respiratory_health_index"]
                        cough_idx = result["cough_index"]
                        stress_idx = result["stress_audio_index"]
                        
                        # Salva leitura acústica no banco
                        reading = AcousticReading(
                            camera_id="galpao-1",
                            respiratory_health_index=resp_health / 100.0, # Normaliza para 0.0 - 1.0
                            cough_index=cough_idx / 100.0,
                            stress_audio_index=stress_idx / 100.0,
                            source="continuous_monitor"
                        )
                        db.session.add(reading)
                        
                        # Se houver pico de tosse ou estresse sonoro severo, emite alerta de evento
                        if cough_idx > 50.0 or stress_idx > 60.0:
                            active_batch = Batch.query.filter(Batch.active == True).first()
                            batch_id = active_batch.id if active_batch else None
                            
                            event = EventLog(
                                camera_id="galpao-1",
                                event_type="acoustic_alert",
                                level="high" if cough_idx > 70.0 else "warning",
                                message=f"Pico acústico detectado: Tosse={cough_idx:.1f}%, Estresse={stress_idx:.1f}%",
                                metadata_json=f'{{"cough_index": {cough_idx}, "stress_index": {stress_idx}}}'
                            )
                            db.session.add(event)
                            
                        db.session.commit()
                        logger.debug("[AudioMonitor] Leitura acústica salva: Tosse=%.1f%%, Resp=%.1f%%", cough_idx, resp_health)
                        
            except Exception as e:
                logger.error("[AudioMonitor] Erro na thread de áudio: %s", e)
                
            time.sleep(self.interval_seconds)
