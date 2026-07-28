import json
import os
import sys
from unittest.mock import patch

import pytest

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))
from supabase_sync_worker import SupabaseSyncWorker


@pytest.fixture
def temp_files(tmp_path):
    log_file = tmp_path / "test_tracking_logs.json"
    state_file = tmp_path / "test_sync_state.json"

    # Escreve logs mockados iniciais no arquivo
    mock_logs = [
        {
            "frame": 1,
            "timestamp": 1716634800.0,
            "detections": [
                {"id": 1, "class": 0, "confidence": 0.9, "smoothed_centroid": [100, 150]}
            ],
        },
        {
            "frame": 2,
            "timestamp": 1716634801.0,
            "detections": [
                {"id": 2, "class": 0, "confidence": 0.85, "smoothed_centroid": [110, 160]}
            ],
        },
    ]
    log_file.write_text(json.dumps(mock_logs))

    return str(log_file), str(state_file)


@pytest.mark.anyio
async def test_sync_worker_success(temp_files):
    log_file, state_file = temp_files
    worker = SupabaseSyncWorker(log_file=log_file, state_file=state_file, interval_seconds=2)

    # Mock do sync_records para simular envio com sucesso
    async def mock_sync_success(records):
        return True

    with patch.object(worker, "sync_records", new=mock_sync_success):
        await worker.run_once()

        # O index deve avançar de 0 para 2 (processou os dois registros do log_file)
        assert worker.last_processed_idx == 2
        assert len(worker.backlog) == 0
        assert worker.current_interval == 2

        # Verifica se o arquivo de estado foi salvo
        assert os.path.exists(state_file)
        with open(state_file, "r") as f:
            state = json.load(f)
            assert state["last_processed_idx"] == 2
            assert len(state["backlog"]) == 0


@pytest.mark.anyio
async def test_sync_worker_network_failure_and_backlog(temp_files):
    log_file, state_file = temp_files
    worker = SupabaseSyncWorker(log_file=log_file, state_file=state_file, interval_seconds=2)

    # Mock do sync_records para simular falha de rede
    async def mock_sync_fail(records):
        return False

    with patch.object(worker, "sync_records", new=mock_sync_fail):
        await worker.run_once()

        # O index avança (foram lidos do log) mas os registros foram movidos para o backlog de falha!
        assert worker.last_processed_idx == 2
        assert len(worker.backlog) == 2
        # Backoff exponencial ativo: intervalo de 2s dobrou para 4s
        assert worker.current_interval == 4

        # Verifica salvamento do estado com backlog
        with open(state_file, "r") as f:
            state = json.load(f)
            assert state["last_processed_idx"] == 2
            assert len(state["backlog"]) == 2


@pytest.mark.anyio
async def test_sync_worker_recovery(temp_files):
    log_file, state_file = temp_files
    worker = SupabaseSyncWorker(log_file=log_file, state_file=state_file, interval_seconds=2)

    # 1. Simula estado anterior com backlog de falha persistido
    initial_backlog = [
        {
            "track_id": 99,
            "class_id": 0,
            "confidence": 0.99,
            "pos_x": 50,
            "pos_y": 50,
            "frame_number": 10,
            "detected_at": "2026-05-25 12:00:00",
        }
    ]
    with open(state_file, "w") as f:
        json.dump({"last_processed_idx": 2, "backlog": initial_backlog}, f)

    worker.load_state()
    worker.current_interval = 8  # Simula que já estava em backoff de 8s

    # 2. Mock do sync com sucesso para a recuperação
    async def mock_sync_success(records):
        return True

    with patch.object(worker, "sync_records", new=mock_sync_success):
        await worker.run_once()

        # Backlog deve ser esvaziado
        assert len(worker.backlog) == 0
        # O intervalo de espera volta para o padrão (2s)
        assert worker.current_interval == 2

        # Verifica persistência pós recuperação
        with open(state_file, "r") as f:
            state = json.load(f)
            assert len(state["backlog"]) == 0
