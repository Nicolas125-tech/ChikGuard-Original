import os
import json
import time
import logging
import paho.mqtt.client as mqtt
from src.core.state import sensor_state
from src.api.fastapi_iot import iot_bridge_state
from src.services.mqtt_gateway import LoRaMqttGateway

logger = logging.getLogger(__name__)

# Configurações do Broker MQTT (pode ser configurado no .env)
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "chikguard/farm/+/sensors")

# Instancia o gateway global para decodificação LoRaWAN
lora_gateway = LoRaMqttGateway()

def on_connect(client, userdata, flags, rc):
    iot_bridge_state["broker_address"] = f"{MQTT_BROKER}:{MQTT_PORT}"
    iot_bridge_state["topic"] = MQTT_TOPIC
    
    if rc == 0:
        iot_bridge_state["mqtt_connected"] = True
        logger.info(f"Conectado ao Broker MQTT em {MQTT_BROKER}:{MQTT_PORT} com sucesso.")
        client.subscribe(MQTT_TOPIC)
        client.subscribe("chikguard/farm/+/sensors/lora")
        logger.info(f"Inscrito nos tópicos IoT: {MQTT_TOPIC} e chikguard/farm/+/sensors/lora")
    else:
        iot_bridge_state["mqtt_connected"] = False
        logger.error(f"Falha na conexão MQTT. Código de retorno: {rc}")

def on_message(client, userdata, msg):
    """
    Callback disparado quando um dispositivo IoT publica dados de sensores.
    Faz o roteamento inteligente: se for no tópico /lora, decodifica o binário.
    Caso contrário, processa o JSON padrão (retrocompatibilidade).
    """
    if msg.topic.endswith("/lora"):
        try:
            lora_gateway.process_message(msg)
            iot_bridge_state["messages_received"] += 1
            iot_bridge_state["last_message_at"] = time.time()
        except Exception as e:
            logger.error(f"Erro na decodificação de telemetria LoRa no tópico {msg.topic}: {e}")
        return

    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        # Atualiza o estado global compartilhado (que a FSM e APIs FastAPI leem)
        if "temperature_c" in data:
            sensor_state["temperature_c"] = float(data["temperature_c"])
        if "humidity_pct" in data:
            sensor_state["humidity_pct"] = float(data["humidity_pct"])
        if "ammonia_ppm" in data:
            sensor_state["ammonia_ppm"] = float(data["ammonia_ppm"])
            
        sensor_state["source"] = "mqtt_esp32"
        sensor_state["updated_at"] = time.time()
        
        iot_bridge_state["messages_received"] += 1
        iot_bridge_state["last_message_at"] = time.time()
        
        logger.debug(f"Sensores atualizados via MQTT ({msg.topic}): Temp {sensor_state['temperature_c']}C | NH3 {sensor_state['ammonia_ppm']}ppm")
        
    except json.JSONDecodeError:
        logger.warning(f"Payload MQTT inválido (não é JSON) no tópico {msg.topic}")
    except Exception as e:
        logger.error(f"Erro ao processar mensagem MQTT: {e}")

async def start_mqtt_bridge():
    """
    Inicia o cliente MQTT em background sem bloquear o Event Loop do FastAPI.
    """
    logger.info("Inicializando a ponte IoT MQTT (Mosquitto/Paho)...")
    
    # Dependendo da versao do paho-mqtt, usa callback_api_version
    try:
        client = mqtt.Client(client_id="chikguard_fastapi_node")
    except Exception:
        # Paho 2.x compatibility
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="chikguard_fastapi_node")
        
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # Usa loop_start que roda numa thread separada gerida pelo Paho
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except ConnectionRefusedError:
        logger.warning(f"Broker MQTT ({MQTT_BROKER}:{MQTT_PORT}) nao encontrado localmente. MQTT Bridge desabilitado.")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado no MQTT: {e}")
        return None
        
    return client
