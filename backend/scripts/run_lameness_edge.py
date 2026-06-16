import json
import logging
import os

# Importa o detector da nossa src
import sys
import time

import cv2
import paho.mqtt.client as mqtt

# Adiciona o backend ao path para resolver os imports absolutos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.vision.lameness_detector import LamenessDetector

# Configuração Básica de Logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuração do MQTT (Broker local ou na nuvem)
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "chikguard/alerts/lameness"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Conectado ao Broker MQTT com sucesso!")
    else:
        logger.error(f"Falha ao conectar ao Broker MQTT, código de retorno: {rc}")


def run_edge_pipeline():
    camera_id = "cam-galpao-01"

    # Você pode testar localmente com a sua webcam (0) ou arquivo mp4
    video_source = "video_granja.mp4"

    # Conexão MQTT
    client = mqtt.Client()
    client.on_connect = on_connect

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()  # Roda a rede do MQTT em uma thread em background
    except Exception as e:
        logger.warning(
            f"MQTT não disponível em {MQTT_BROKER}. Os eventos serão apenas impressos no log. Erro: {e}"
        )
        client = None

    # Inicialização da Câmera / Stream
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        logger.error(f"Não foi possível abrir o vídeo/stream: {video_source}")
        return

    # Instanciando o modelo (Ajuste para TensorRT se disponível: yolov8n-pose.engine)
    logger.info("Carregando o modelo de Pose e ByteTrack...")
    detector = LamenessDetector(model_path="yolov8n-pose.pt", history_size=45)

    logger.info("Iniciando a inferência na Borda (Edge)...")

    while True:
        success, frame = cap.read()
        if not success:
            logger.info("Fim do stream de vídeo.")
            break

        # Processamento e Detecção
        start_time = time.time()
        result, lame_events = detector.process_frame(frame, camera_id)
        fps = 1.0 / (time.time() - start_time)

        # Envio de Mensageria Assíncrona
        for event in lame_events:
            event_json = json.dumps(event)
            logger.warning(
                f"ALERTA: Claudicação Detectada! Ave ID: {event['bird_id']} | Confiança: {event['confidence'] * 100:.1f}%"
            )
            logger.warning(f"Detalhes: {event['metadata']}")

            if client:
                client.publish(MQTT_TOPIC, event_json)

        # Opcional: Renderizar o vídeo com os keypoints no monitor local para debug
        annotated_frame = result.plot()
        cv2.putText(
            annotated_frame,
            f"FPS: {fps:.1f}",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

        # Diminuir o tamanho da janela para caber na tela, se necessário
        annotated_frame = cv2.resize(annotated_frame, (1024, 768))
        cv2.imshow("ChikGuard - Edge Pose Analysis", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            logger.info("Interrompido pelo usuário.")
            break

    # Limpeza
    cap.release()
    cv2.destroyAllWindows()
    if client:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run_edge_pipeline()
