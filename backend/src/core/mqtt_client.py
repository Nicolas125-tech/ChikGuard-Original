import json
import logging

from paho.mqtt.client import CallbackAPIVersion, Client, MQTTv311

logger = logging.getLogger("chikguard.mqtt")


class ChikGuardMQTTClient:
    """
    Cliente MQTT para integração com IoT e Sensores da Granja (Fase 2).
    Conecta a um Broker, escuta tópicos de telemetria e aciona atuadores.
    """

    def __init__(self, broker_url="mqtt.eclipseprojects.io", port=1883, app_context_fn=None):
        self.broker_url = broker_url
        self.port = port
        self.app_context_fn = app_context_fn
        self.client = Client(CallbackAPIVersion.VERSION1, client_id="chikguard_backend", protocol=MQTTv311)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self._running = False

    def start(self):
        """Inicia a conexão e o loop MQTT assincronamente."""
        if self._running:
            return
        self._running = True
        try:
            self.client.connect(self.broker_url, self.port, 60)
            self.client.loop_start()
            logger.info(f"[MQTT] Iniciado e conectando a {self.broker_url}:{self.port}...")
        except Exception as e:
            logger.error(f"[MQTT] Falha ao iniciar: {e}")

    def stop(self):
        """Para o cliente MQTT."""
        self._running = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("[MQTT] Cliente desconectado.")

    def publish_actuator(self, camera_id: str, action: str, payload: dict):
        """Publica comando para atuar em exaustores/aquecedores."""
        topic = f"chikguard/{camera_id}/actuators/{action}"
        try:
            self.client.publish(topic, json.dumps(payload), qos=1)
            logger.info(f"[MQTT] Comando publicado em {topic}: {payload}")
        except Exception as e:
            logger.error(f"[MQTT] Erro ao publicar em {topic}: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("[MQTT] Conectado ao Broker com sucesso!")
            # Inscrever-se nos tópicos de todas as granjas
            client.subscribe("chikguard/+/sensors/telemetry")
        else:
            logger.error(f"[MQTT] Falha de conexão. Código de retorno: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"[MQTT] Desconectado. Código: {rc}")

    def _on_message(self, client, userdata, msg):
        """Callback executado ao receber mensagens dos sensores."""
        try:
            topic_parts = msg.topic.split("/")
            if len(topic_parts) >= 3 and topic_parts[2] == "sensors":
                camera_id = topic_parts[1]
                payload = json.loads(msg.payload.decode("utf-8"))

                # Executa no contexto do Flask para salvar no banco de dados
                if self.app_context_fn:
                    with self.app_context_fn():
                        self._process_telemetry(camera_id, payload)
        except Exception as e:
            logger.error(f"[MQTT] Erro ao processar mensagem: {e}")

    def _process_telemetry(self, camera_id: str, payload: dict):
        """Salva a leitura de temperatura/umidade real vinda do IoT."""
        from database import SensorReading, db

        temp = payload.get("temperature")
        hum = payload.get("humidity")
        ammonia = payload.get("ammonia")

        reading = SensorReading(
            camera_id=camera_id,
            temperature_c=temp,
            humidity_pct=hum,
            ammonia_ppm=ammonia,
            source="mqtt_iot",
        )
        db.session.add(reading)
        db.session.commit()
        logger.debug(f"[MQTT] Telemetria salva para {camera_id}: {payload}")

        if getattr(self, "automation_engine", None):
            try:
                self.automation_engine.process_telemetry(
                    camera_id,
                    float(temp) if temp is not None else 0.0,
                    float(hum) if hum is not None else 0.0,
                    float(ammonia) if ammonia is not None else 0.0
                )
            except Exception as e:
                logger.error(f"[MQTT] Erro ao disparar motor de automacao: {e}")
