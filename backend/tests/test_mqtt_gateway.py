import os
import sys
import struct
import pytest
from unittest.mock import MagicMock

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Mock do cv2 para evitar erros na inicialização de módulos de visão do app
import unittest.mock as mock

# Configuração de variáveis de ambiente para testes
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from database import SensorReading, db
from src.core.state import sensor_state, sensor_thresholds
from src.core.state_machine import BusinessStateMachine
from flask import Flask

# Importamos o serviço que será desenvolvido na Fase GREEN
from src.services.mqtt_gateway import LoRaMqttGateway

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


def test_lora_payload_decoding_and_persistence(db_session):
    """
    Testa se o payload LoRaWAN binário de 7 bytes é decodificado corretamente,
    se atualiza o estado em memória dos sensores e se persiste no SQLite local como PENDING.
    """
    # 7 bytes binários:
    # node_id = 1 (1 byte, uint8) -> 0x01
    # temp = 28.5 (2 bytes, int16, 285) -> 0x011D
    # hum = 65 (1 byte, uint8) -> 0x41
    # nh3 = 12.50 (2 bytes, uint16, 1250) -> 0x04E2
    # bat = 95 (1 byte, uint8) -> 0x5F
    payload = struct.pack(">BhBHB", 1, 285, 65, 1250, 95)
    assert len(payload) == 7

    # Instancia o gateway fornecendo a sessão do banco mockada
    gateway = LoRaMqttGateway(db_session=db_session)
    
    # Simula o recebimento de mensagem MQTT no tópico da granja
    msg = MagicMock()
    msg.topic = "chikguard/farm/galpao-1/sensors/lora"
    msg.payload = payload

    # Executa processamento
    gateway.process_message(msg)

    # 1. Valida atualização do estado global em memória (para a FSM ler)
    assert sensor_state["temperature_c"] == 28.5
    assert sensor_state["humidity_pct"] == 65.0
    assert sensor_state["ammonia_ppm"] == 12.50
    assert sensor_state["source"] == "lora_node_1"

    # 2. Valida persistência física no banco de dados local SQLite
    readings = db_session.query(SensorReading).all()
    assert len(readings) == 1
    reading = readings[0]
    
    assert reading.camera_id == "galpao-1"
    assert reading.temperature_c == 28.5
    assert reading.humidity_pct == 65.0
    assert reading.ammonia_ppm == 12.50
    assert reading.source == "lora_node_1"
    assert reading.sync_status == "PENDING"  # Regra de offline-first


def test_lora_payload_invalid_size(db_session):
    """
    Garante que o gateway seja resiliente a pacotes corrompidos ou incompletos
    e não lance exceções, apenas descarte o pacote de forma segura.
    """
    # Envia payload de 5 bytes (inválido para o struct de 7 bytes)
    payload_incompleto = struct.pack(">Bhh", 1, 285, 65)
    
    gateway = LoRaMqttGateway(db_session=db_session)
    msg = MagicMock()
    msg.topic = "chikguard/farm/galpao-1/sensors/lora"
    msg.payload = payload_incompleto

    # Não deve lançar erro
    try:
        gateway.process_message(msg)
    except Exception as e:
        pytest.fail(f"Gateway falhou ao receber dados corrompidos: {e}")

    # Não deve ter adicionado nada ao banco de dados
    readings = db_session.query(SensorReading).all()
    assert len(readings) == 0


def test_lora_gateway_fsm_integration(db_session):
    """
    Valida a integração dos dados atualizados pelo gateway com o ciclo da FSM.
    Ao decodificar temperatura extrema (ex: 35.0°C), a FSM deve mandar ligar a ventilação.
    """
    # Temperatura alta de 35.0°C -> 350
    payload = struct.pack(">BhBHB", 1, 350, 60, 500, 90)
    
    gateway = LoRaMqttGateway(db_session=db_session)
    msg = MagicMock()
    msg.topic = "chikguard/farm/galpao-1/sensors/lora"
    msg.payload = payload

    # Gateway processa a mensagem
    gateway.process_message(msg)

    # Executamos a FSM com o estado global atualizado
    fsm = BusinessStateMachine()
    context = {
        "temp_atual": sensor_state["temperature_c"],
        "ventilacao_on": False,
        "aquecedor_on": False,
        "hour": 12,
        "targets": {
            "fan_on_temp": sensor_thresholds["temp_max"], # 32.0
            "fan_off_temp": sensor_thresholds["temp_max"] - 1.0,
            "heater_on_temp": sensor_thresholds["temp_min"], # 18.0
            "heater_off_temp": sensor_thresholds["temp_min"] + 1.0,
            "batch_age_day": 21
        },
        "intrusion_active": False,
        "preheat_recommended": False
    }

    fsm_output = fsm.process_context(context)

    # Com temperatura atual em 35.0°C (acima do threshold de 32.0°C), a ventilação deve ligar!
    assert fsm_output["ventilacao"] is True
    assert fsm_output["aquecedor"] is False
