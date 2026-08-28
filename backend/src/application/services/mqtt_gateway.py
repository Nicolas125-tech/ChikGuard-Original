import time
import struct
import logging
from datetime import datetime, timezone
from src.core.state import sensor_state
from database import SensorReading

logger = logging.getLogger("chikguard.lora_gateway")


class LoRaMqttGateway:
    """
    Gateway MQTT responsável por receber, decodificar e processar os pacotes binários
    LoRaWAN enviados pelos nós sensores distribuídos nos galpões metálicos.
    """

    def __init__(self, db_session=None):
        self.db_session = db_session

    def process_message(self, msg):
        """
        Processa e decodifica uma mensagem recebida do broker MQTT.
        Payload esperado: 7 bytes estruturados em Big-Endian (>BhBHB):
          - Byte 0: Sensor ID (uint8)
          - Bytes 1-2: Temperatura (int16, dividida por 10)
          - Byte 3: Umidade (uint8)
          - Bytes 4-5: Amônia (uint16, dividida por 100)
          - Byte 6: Bateria (uint8)
        """
        payload = msg.payload
        topic = msg.topic

        # Validação resiliente de tamanho do pacote
        if len(payload) != 7:
            logger.warning(
                f"[Gateway LoRa] Pacote descartado. Tamanho incorreto (esperado: 7 bytes, recebido: {len(payload)} bytes) no tópico {topic}."
            )
            return

        try:
            # Decodifica o payload binário
            # > = Big Endian (Network Byte Order)
            # B = uint8 (node_id)
            # h = int16 (temperature * 10)
            # B = uint8 (humidity)
            # H = uint16 (ammonia * 100)
            # B = uint8 (battery_pct)
            node_id, temp_raw, hum_raw, nh3_raw, bat_raw = struct.unpack(">BhBHB", payload)

            # Conversão para as escalas corretas
            temperature_c = float(temp_raw) / 10.0
            humidity_pct = float(hum_raw)
            ammonia_ppm = float(nh3_raw) / 100.0
            battery_pct = bat_raw

            logger.info(
                f"[Gateway LoRa] Sensor {node_id} decodificado: Temp={temperature_c}°C, "
                f"Hum={humidity_pct}%, NH3={ammonia_ppm}ppm, Bateria={battery_pct}%"
            )

            # 1. Atualiza o estado global em memória (lido de forma assíncrona pela FSM de controle)
            sensor_state.update({
                "temperature_c": temperature_c,
                "humidity_pct": humidity_pct,
                "ammonia_ppm": ammonia_ppm,
                "source": f"lora_node_{node_id}",
                "updated_at": time.time(),
            })

            # Extrai o camera_id / galpao_id a partir do tópico (ex: chikguard/farm/galpao-1/sensors/lora)
            # Formato esperado: chikguard/farm/{camera_id}/sensors/lora
            parts = topic.split("/")
            if len(parts) >= 3:
                camera_id = parts[2]
            else:
                camera_id = f"galpao-{node_id}"

            # 2. Persistência local no banco SQLite com suporte a Store & Forward (Offline-First)
            reading = SensorReading(
                camera_id=camera_id,
                temperature_c=temperature_c,
                humidity_pct=humidity_pct,
                ammonia_ppm=ammonia_ppm,
                source=f"lora_node_{node_id}",
                sync_status="PENDING",
                timestamp=datetime.now(timezone.utc)
            )

            if self.db_session:
                # Caso uma sessão tenha sido injetada (Testes)
                self.db_session.add(reading)
                self.db_session.commit()
            else:
                # Em ambiente de execução real, inicializa sessão do FastAPI
                from src.infrastructure.db.session import SessionLocal
                session = SessionLocal()
                try:
                    session.add(reading)
                    session.commit()
                except Exception as db_err:
                    session.rollback()
                    logger.error(f"[Gateway LoRa] Erro ao salvar dados no SQLite local: {db_err}")
                finally:
                    session.close()

        except Exception as e:
            logger.error(f"[Gateway LoRa] Falha inesperada ao decodificar payload: {e}")
