import os
import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Mock do cv2
import unittest.mock as mock
sys.modules["cv2"] = mock.MagicMock()

# Configuração de variáveis de ambiente para testes
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from database import SensorReading, db
from src.services.sensor_sync_worker import SensorSyncWorker
from flask import Flask

app = Flask(__name__)
app.config["TESTING"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


@pytest.fixture
def db_session():
    """Cria banco de dados em memória para os testes."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


import asyncio


def test_sensor_sync_success(db_session):
    """
    Testa a sincronização bem-sucedida de registros PENDING.
    Os registros devem ser enviados ao Supabase e marcados localmente como SYNCED.
    """
    reading1 = SensorReading(
        camera_id="galpao-1",
        temperature_c=25.5,
        humidity_pct=60.0,
        ammonia_ppm=10.0,
        source="lora_node_1",
        sync_status="PENDING",
        timestamp=datetime.now(timezone.utc)
    )
    reading2 = SensorReading(
        camera_id="galpao-1",
        temperature_c=26.0,
        humidity_pct=62.0,
        ammonia_ppm=11.0,
        source="lora_node_1",
        sync_status="PENDING",
        timestamp=datetime.now(timezone.utc)
    )
    db_session.add_all([reading1, reading2])
    db_session.commit()

    supabase_mock = MagicMock()
    supabase_mock.table.return_value.insert.return_value.execute = MagicMock()

    worker = SensorSyncWorker(db_session=db_session, supabase_client=supabase_mock, interval_seconds=2)
    
    asyncio.run(worker.run_once())

    assert reading1.sync_status == "SYNCED"
    assert reading2.sync_status == "SYNCED"
    assert reading1.last_sync_attempt is not None

    supabase_mock.table.assert_called_with("sensor_readings")
    assert supabase_mock.table.return_value.insert.called


def test_sensor_sync_network_failure_keeps_local_data(db_session):
    """
    Garante que falhas de rede no Supabase mudem o status para FAILED no local,
    sem perda de dados (Offline-First), e ativem backoff exponencial.
    """
    reading = SensorReading(
        camera_id="galpao-1",
        temperature_c=27.0,
        humidity_pct=65.0,
        ammonia_ppm=12.0,
        source="lora_node_1",
        sync_status="PENDING",
        timestamp=datetime.now(timezone.utc)
    )
    db_session.add(reading)
    db_session.commit()

    supabase_mock = MagicMock()
    supabase_mock.table.return_value.insert.return_value.execute.side_effect = Exception("Network timeout")

    worker = SensorSyncWorker(db_session=db_session, supabase_client=supabase_mock, interval_seconds=2)
    
    asyncio.run(worker.run_once())

    assert reading.sync_status == "FAILED"
    assert worker.current_interval == 4


def test_sensor_sync_recovery_from_failed(db_session):
    """
    Testa se o worker recupera registros FAILED quando a rede é reestabelecida,
    e reseta o intervalo de backoff para o valor padrão.
    """
    reading = SensorReading(
        camera_id="galpao-1",
        temperature_c=24.0,
        humidity_pct=58.0,
        ammonia_ppm=8.0,
        source="lora_node_1",
        sync_status="FAILED",
        timestamp=datetime.now(timezone.utc)
    )
    db_session.add(reading)
    db_session.commit()

    supabase_mock = MagicMock()
    supabase_mock.table.return_value.insert.return_value.execute = MagicMock()

    worker = SensorSyncWorker(db_session=db_session, supabase_client=supabase_mock, interval_seconds=2)
    worker.current_interval = 8

    asyncio.run(worker.run_once())

    assert reading.sync_status == "SYNCED"
    assert worker.current_interval == 2
