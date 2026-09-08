import logging
import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np

# Mock heavy modules before anything else
sys.modules['cv2'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['supervision'] = MagicMock()

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault("SUPABASE_JWT_SECRET", "test_jwt_secret_key_for_unit_testing_32bytes")
os.environ.setdefault("ENABLE_SAHI", "false")

from src.application.cv_master.cv_runner import SOTAPipelineRunner  # noqa: E402


def test_save_reading_error_handling(caplog):
    """
    Testa se o pipeline de visão computacional continua a executar
    mesmo que a gravação de uma leitura térmica no banco de dados falhe (teste de edge case).
    """
    with patch("src.application.cv_master.cv_runner.SessionLocal") as mock_session_local, \
         patch("src.application.cv_master.cv_runner.cv2"), \
         patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_cls, \
         patch("src.application.cv_master.cv_runner.time.sleep"), \
         patch("src.application.cv_master.cv_runner.time.time", side_effect=[100.0, 100.0, 100.0, 100.0, 100.0]), \
         patch("src.application.cv_master.cv_runner.np.mean") as mock_mean, \
         patch("src.application.cv_master.cv_runner.SOTAInferenceEngine"):

        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Simulated DB Error")
        mock_session_local.return_value = mock_db

        mock_mean.return_value = 127.5

        class MockExecutor:
            def __init__(self, max_workers=2):
                pass
            def submit(self, fn, *args, **kwargs):
                fn(*args, **kwargs)
                return MagicMock()
            def shutdown(self, wait=True):
                pass
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb): pass

        mock_executor_cls.return_value = MockExecutor()

        # We need to patch queue.Queue which is imported *inside* _run_loop
        # So we patch 'queue.Queue' directly
        with patch('src.application.cv_master.cv_runner.time.perf_counter', return_value=1.0), \
             patch('src.application.cv_master.cv_runner.threading.Thread'), \
             patch('queue.Queue') as mock_queue_cls, \
             patch('src.application.cv_master.cv_runner.asyncio.new_event_loop') as mock_loop:

            mock_queue = MagicMock()
            def get_side_effect(*args, **kwargs):
                runner.running = False # Stop loop after this frame
                return np.zeros((480, 640, 3), dtype=np.uint8)

            mock_queue.get.side_effect = get_side_effect
            mock_queue_cls.return_value = mock_queue

            # Create a mock loop for the SOTAPipelineRunner
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance

            runner = SOTAPipelineRunner()
            runner.running = True

            # mock missing attributes that might be required
            runner.engine = MagicMock()
            runner.bg_subtractor = MagicMock()
            runner.tracker = MagicMock()
            runner.behavior = MagicMock()
            runner.species_classifier = MagicMock()
            runner.pose_analyzer = MagicMock()
            runner.gait_analyzer = MagicMock()
            runner.perf_metrics = MagicMock()
            runner.behavior.dead_or_sick_ids = set()
            runner.tracker.update_with_detections.return_value = []

            # Run the pipeline
            with caplog.at_level(logging.ERROR):
                runner._run_loop()

            # Check if the error was logged
            assert "Erro ao salvar leitura termica: Simulated DB Error" in caplog.text

def test_tamper_alert_db_error_handling(caplog):
    """
    Testa se o tratamento de erro no _emit_tamper_alerts
    funciona corretamente e a notificação é feita mesmo se
    a gravação no banco falhar.
    """
    import src.core.state as state

    with patch("src.application.cv_master.cv_runner.SessionLocal") as mock_session_local, \
         patch("src.application.cv_master.cv_runner.asyncio.run_coroutine_threadsafe") as mock_emit, \
         patch("src.application.cv_master.cv_runner.emit_new_alert", new=MagicMock()) as _:

        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Simulated DB Tamper Error")
        mock_session_local.return_value = mock_db

        runner = SOTAPipelineRunner()
        runner.loop = MagicMock()

        # Override cooldown checking state to ensure it attempts to emit
        state.tamper_state["last_alert_ts"] = 0.0

        with caplog.at_level(logging.ERROR):
            runner._emit_tamper_alerts(["camera_obstruida"], 1000.0)

        assert "Erro ao salvar alerta de tamper no DB: Simulated DB Tamper Error" in caplog.text
        # Assert that the alert is still emitted even if DB fails
        mock_emit.assert_called_once()
