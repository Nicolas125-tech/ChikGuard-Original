import pytest
import sys
import os
from datetime import datetime

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock do cv2 para evitar erros na inicialização de módulos de visão do app
import unittest.mock as mock
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
from database import db, Batch, BatchLogbook
from src.agents.base import ClimateAgent
from weather_forecast.plugin import WeatherForecastPlugin
from src.core.state_machine import BusinessStateMachine

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

@pytest.fixture
def weather_plugin():
    plugin = WeatherForecastPlugin()
    return plugin

def test_climate_agent_normal_conditions(test_client, weather_plugin):
    """Testa a recomendação de climatização sob condições normais."""
    # Define condições normais
    weather_plugin.set_mock_conditions(temp_c=25.0, heatwave=False, cold_snap=False)
    
    agent = ClimateAgent(weather_plugin=weather_plugin)
    result = agent.run()
    
    assert result["status"] == "COMPLETED"
    assert len(result["adjustments"]) == 0
    # Alvos padrão mantidos
    assert result["recommended_targets"]["fan_on_temp"] == 32.0
    assert result["recommended_targets"]["heater_on_temp"] == 24.0

def test_climate_agent_heatwave_adjustment(test_client, weather_plugin):
    """Testa o ajuste preditivo do ventilador para mais cedo durante uma onda de calor."""
    # Simula lote ativo
    batch = Batch(camera_id="galpao-1", name="Batch Teste Calor", active=True)
    db.session.add(batch)
    db.session.commit()

    # Define onda de calor iminente
    weather_plugin.set_mock_conditions(temp_c=34.0, heatwave=True, cold_snap=False)
    
    agent = ClimateAgent(weather_plugin=weather_plugin)
    result = agent.run({"camera_id": "galpao-1"})
    
    assert result["status"] == "COMPLETED"
    assert len(result["adjustments"]) > 0
    # Limites reduzidos preventivamente para ligar antes
    assert result["recommended_targets"]["fan_on_temp"] == 30.0
    assert result["recommended_targets"]["fan_off_temp"] == 29.0
    
    # Testa a integração com a FSM (garantindo que ela liga a ventilação a 30.5°C)
    fsm = BusinessStateMachine()
    
    context = {
        'temp_atual': 30.5,
        'targets': result["recommended_targets"],
        'hour': 12,
        'intrusion_active': False,
        'preheat_recommended': False,
        'ventilacao_on': False,
        'aquecedor_on': False
    }
    
    fsm_output = fsm.process_context(context)
    # Sob o alvo padrão (32°C), estaria desligada. Sob o alvo adaptado (30°C), liga!
    assert fsm_output["ventilacao"] is True
    assert fsm_output["aquecedor"] is False

def test_state_machine_hard_limits(test_client):
    """Garante que a FSM ignora alvos do agente/usuário que ultrapassem limites seguros."""
    fsm = BusinessStateMachine()
    
    # Simula alvos absurdamente perigosos sugeridos (ex: alucinação de LLM ou erro de usuário)
    # Ligar ventilador apenas a 45°C (as aves morreriam de calor antes)
    # Ligar aquecedor apenas a 10°C (as aves morreriam de frio antes)
    perilous_targets = {
        "fan_on_temp": 45.0,
        "fan_off_temp": 44.0,
        "heater_on_temp": 10.0,
        "heater_off_temp": 11.0,
        "target_temp": 28.0
    }
    
    # Cenário de Calor (Temperatura atual = 35°C)
    # Sem watchdog, o ventilador ficaria desligado (já que fan_on está em 45°C)
    context_hot = {
        'temp_atual': 35.0,
        'targets': perilous_targets,
        'hour': 12,
        'intrusion_active': False,
        'preheat_recommended': False,
        'ventilacao_on': False,
        'aquecedor_on': False
    }
    
    hot_output = fsm.process_context(context_hot)
    # Watchdog deve limitar o fan_on a 34°C max. Como temp_atual (35°C) > 34°C, liga a ventilação!
    assert hot_output["ventilacao"] is True

    # Cenário de Frio (Temperatura atual = 17°C)
    # Sem watchdog, o aquecedor estaria desligado (já que heater_on está em 10°C)
    context_cold = {
        'temp_atual': 17.0,
        'targets': perilous_targets,
        'hour': 12,
        'intrusion_active': False,
        'preheat_recommended': False,
        'ventilacao_on': False,
        'aquecedor_on': False
    }
    
    cold_output = fsm.process_context(context_cold)
    # Watchdog deve forçar heater_on para no mínimo 18°C. Como temp_atual (17°C) < 18°C, liga o aquecedor!
    assert cold_output["aquecedor"] is True
