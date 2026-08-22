import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
import sys
from datetime import datetime

import pytest

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Mock do cv2 para evitar erros na inicialização de módulos de visão do app
import unittest.mock as mock

sys.modules["cv2"] = mock.MagicMock()

# Configuração de variáveis de ambiente para testes do Flask
os.environ["FLASK_ENV"] = "testing"
os.environ["SUPABASE_JWT_SECRET"] = os.environ.get("SUPABASE_JWT_SECRET", "dummy_secret_dummy_secret_dummy_secret_for_tests_32bytes")
os.environ["ADMIN_PASSWORD"] = "testpassword"
os.environ["ADMIN_EMAIL"] = "test@example.com"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["CORS_ALLOWED_ORIGINS"] = "*"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app_flask_legacy import app
from database import AcousticReading, Batch, BatchLogbook, EventLog, SensorReading, db
from src.agents.base import VetWelfareAgent


@pytest.fixture
def test_client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


def test_vet_welfare_agent_normal(test_client):
    """Testa o agente veterinário operando em condições ótimas (status NORMAL)."""
    # Cria o lote ativo
    batch = Batch(camera_id="galpao-1", name="Batch Teste Normal", active=True)
    db.session.add(batch)

    # Insere leitura física normal
    s1 = SensorReading(
        camera_id="galpao-1",
        temperature_c=25.0,
        humidity_pct=60.0,
        ammonia_ppm=4.0,
        timestamp=datetime.utcnow(),
    )
    db.session.add(s1)

    # Insere leitura acústica saudável
    a1 = AcousticReading(
        camera_id="galpao-1",
        respiratory_health_index=0.95,
        cough_index=0.05,
        stress_audio_index=0.1,
        timestamp=datetime.utcnow(),
    )
    db.session.add(a1)
    db.session.commit()

    # Executa o agente
    agent = VetWelfareAgent()
    result = agent.run({"camera_id": "galpao-1"})

    assert result["status"] == "COMPLETED"
    assert result["welfare_status"] == "NORMAL"
    assert len(result["anomalies"]) == 0
    assert result["logbook_entry_created"] is False


def test_vet_welfare_agent_critical_ammonia(test_client):
    """Testa a reação do agente veterinário a níveis críticos de amônia."""
    # Cria o lote ativo
    batch = Batch(camera_id="galpao-1", name="Batch Teste Amonia", active=True)
    db.session.add(batch)

    # Insere leitura física crítica de amônia (> 20 ppm)
    s1 = SensorReading(
        camera_id="galpao-1",
        temperature_c=25.0,
        humidity_pct=60.0,
        ammonia_ppm=22.5,
        timestamp=datetime.utcnow(),
    )
    db.session.add(s1)
    db.session.commit()

    # Executa o agente
    agent = VetWelfareAgent()
    result = agent.run({"camera_id": "galpao-1"})

    assert result["status"] == "COMPLETED"
    assert result["welfare_status"] == "CRITICAL"
    assert any("amônia" in anomaly.lower() for anomaly in result["anomalies"])
    assert result["logbook_entry_created"] is True

    # Verifica se a nota de diagnóstico clínico foi salva no diário do lote (BatchLogbook)
    entry = BatchLogbook.query.filter_by(author="Agent_VetWelfare").first()
    assert entry is not None
    assert "amônia" in entry.note.lower()


def test_vet_welfare_agent_critical_acoustics_and_carcass(test_client):
    """Testa a detecção combinada de estresse respiratório e alertas visuais de carcaça."""
    # Cria o lote ativo
    batch = Batch(camera_id="galpao-1", name="Batch Teste Completo", active=True)
    db.session.add(batch)

    # Insere leitura acústica severa (tosse excessiva e respiração ruim)
    a1 = AcousticReading(
        camera_id="galpao-1",
        respiratory_health_index=0.5,
        cough_index=0.75,
        stress_audio_index=0.2,
        timestamp=datetime.utcnow(),
    )
    db.session.add(a1)

    # Insere evento de alerta visual de carcaça (ave morta detectada por CV)
    event = EventLog(
        camera_id="galpao-1",
        event_type="carcass_alert",
        level="critical",
        message="Aves mortas detectadas na zona central do galpão",
        timestamp=datetime.utcnow(),
    )
    db.session.add(event)
    db.session.commit()

    # Executa o agente
    agent = VetWelfareAgent()
    result = agent.run({"camera_id": "galpao-1"})

    assert result["status"] == "COMPLETED"
    assert result["welfare_status"] == "CRITICAL"
    assert len(result["anomalies"]) >= 2
    assert any("carcaça" in anomaly.lower() for anomaly in result["anomalies"])
    assert any("tosse" in anomaly.lower() for anomaly in result["anomalies"])
    assert result["logbook_entry_created"] is True


def test_vet_welfare_agent_diagnostic_note_weight_exception(test_client):
    """Testa se a exceção ao buscar WeightEstimate em _generate_diagnostic_note é capturada graciosamente sem falhar a geração do relatório."""
    agent = VetWelfareAgent()
    averages = {"temp": 25.0, "humi": 60.0, "amon": 5.0, "thi": 70.0, "resp": 0.9, "cough": 0.0, "stress": 0.1}
    counts = {"carcass": 0, "prostration": 0, "immobility": 0, "behavior": 0}
    with mock.patch("database.WeightEstimate.query") as mock_query:
        mock_query.order_by.side_effect = Exception("DB Connection Error")
        summary = agent._generate_diagnostic_note("NORMAL", averages, counts, [], [])
        assert "[Diagnóstico Veterinário - NORMAL]" in summary
        assert "Desempenho de Marcha/Peso" not in summary


def test_vet_welfare_agent_fetch_telemetry_db_exception(test_client):
    """Testa a propagação de exceção no método fetch_telemetry quando ocorre falha no banco de dados."""
    agent = VetWelfareAgent()
    with mock.patch("database.SensorReading.query") as mock_query:
        mock_query.filter.side_effect = Exception("Database query failed")
        with pytest.raises(Exception, match="Database query failed"):
            agent.fetch_telemetry()
