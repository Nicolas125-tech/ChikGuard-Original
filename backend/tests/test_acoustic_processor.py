import pytest
import sys
import os
import unittest.mock as mock
from datetime import datetime

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock do cv2 para evitar erros na inicialização de módulos de visão do app
sys.modules['cv2'] = mock.MagicMock()

# Configuração de variáveis de ambiente para testes do Flask
os.environ["FLASK_ENV"] = "testing"
os.environ["SUPABASE_JWT_SECRET"] = "dummy_secret_for_tests"
os.environ["ADMIN_PASSWORD"] = "testpassword"
os.environ["ADMIN_EMAIL"] = "test@example.com"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["CORS_ALLOWED_ORIGINS"] = "*"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import app
from database import db, AcousticReading, EventLog, Batch
from src.audio.acoustic_processor import ContinuousAudioMonitor

@pytest.fixture
def test_client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    with app.app_context():
        db.create_all()
        # Inicializa dados básicos de lote
        batch = Batch(camera_id="galpao-1", name="Batch Teste Audio", active=True)
        db.session.add(batch)
        db.session.commit()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture
def mock_classifier():
    classifier = mock.MagicMock()
    return classifier

def test_audio_monitor_healthy(test_client, mock_classifier):
    """Valida a inserção de leituras normais no banco de dados sem geração de alertas."""
    # Configura mock para retornar resposta saudável
    mock_classifier.classify.return_value = {
        "respiratory_health_index": 98.0,
        "cough_index": 5.0,
        "stress_audio_index": 12.0
    }
    
    def app_context_fn():
        return app.app_context()
        
    monitor = ContinuousAudioMonitor(classifier=mock_classifier, app_context_fn=app_context_fn, interval_seconds=1.0)
    
    # Executa ciclo manualmente (sem disparar thread de loop infinito nos testes)
    monitor._running = True
    monitor._run()
    
    # Verifica que salvou no banco
    readings = AcousticReading.query.all()
    assert len(readings) == 1
    assert readings[0].respiratory_health_index == 0.98
    assert readings[0].cough_index == 0.05
    
    # Sem alertas gerados
    alerts = EventLog.query.filter_by(event_type="acoustic_alert").all()
    assert len(alerts) == 0

def test_audio_monitor_distress_alert(test_client, mock_classifier):
    """Valida a geração de alertas clínicos (EventLog) caso haja tosse excessiva."""
    # Configura mock para retornar tosse elevada
    mock_classifier.classify.return_value = {
        "respiratory_health_index": 45.0,
        "cough_index": 75.0,
        "stress_audio_index": 40.0
    }
    
    def app_context_fn():
        return app.app_context()
        
    monitor = ContinuousAudioMonitor(classifier=mock_classifier, app_context_fn=app_context_fn, interval_seconds=1.0)
    
    monitor._running = True
    monitor._run()
    
    # Verifica leitura no banco
    readings = AcousticReading.query.all()
    assert len(readings) == 1
    assert readings[0].cough_index == 0.75
    
    # Alerta crítico gerado com sucesso
    alerts = EventLog.query.filter_by(event_type="acoustic_alert").all()
    assert len(alerts) == 1
    assert alerts[0].level == "high"
    assert "Pico acústico" in alerts[0].message
