from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from database import db, User, Reading, BirdSnapshot
import cv2
import numpy as np
import threading
import time
import os
import random
from ultralytics import YOLO 

# ======================================================================================
# --- CONFIGURAÇÃO DE DETECÇÃO ---
# Mude para 'aves' para o modo de produção ou 'objetos' para teste geral.
MODO_DETECCAO = 'aves'
# ======================================================================================

# --- CONFIGURAÃ‡ÃƒO FINA DA IA ---
# Aumentar `INFERENCE_IMGSZ` melhora objetos pequenos/distantes.
INFERENCE_IMGSZ = int(os.getenv("INFERENCE_IMGSZ", "960"))
# Limiar mais baixo ajuda aves distantes; a confirmaÃ§Ã£o temporal reduz falsos positivos.
DETECTION_CONF = float(os.getenv("DETECTION_CONF", "0.22"))
DETECTION_IOU = float(os.getenv("DETECTION_IOU", "0.45"))
MIN_BIRD_AREA_RATIO = float(os.getenv("MIN_BIRD_AREA_RATIO", "0.00003"))
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
BIRD_CLASS_NAME = os.getenv("BIRD_CLASS_NAME", "bird")
TRACKER_TYPE = os.getenv("TRACKER_TYPE", "bytetrack").strip().lower()
TRACKER_CONFIG = "botsort.yaml" if TRACKER_TYPE == "botsort" else "bytetrack.yaml"
BIRD_SNAPSHOT_SAVE_INTERVAL = int(os.getenv("BIRD_SNAPSHOT_SAVE_INTERVAL", "10"))
BIRD_LIVE_TTL_SEC = int(os.getenv("BIRD_LIVE_TTL_SEC", "4"))

class ObjectDetector:
    def __init__(self, model_path='yolov8n.pt'):
        self.yolo_loaded = False
        self.model = None
        try:
            self.model = YOLO(model_path)
            self.yolo_loaded = True
            print(f"Modelo Ultralytics '{model_path}' carregado com sucesso.")
            self.model.predict(np.zeros((480, 640, 3)), verbose=False)
            print("Modelo aquecido e pronto para uso.")
        except Exception as e:
            print(f"Erro ao carregar o modelo Ultralytics: {e}")
            print("Verifique o caminho do modelo e dependencias.")

    def detect(self, frame):
        if not self.yolo_loaded:
            return []

        results = self.model.track(
            frame,
            verbose=False,
            persist=True,
            tracker=TRACKER_CONFIG,
            conf=DETECTION_CONF,
            iou=DETECTION_IOU,
            imgsz=INFERENCE_IMGSZ
        )
        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        class_ids = boxes.cls.cpu().numpy().astype(int)
        confidences = boxes.conf.cpu().numpy()
        track_ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else np.full(len(xyxy), -1, dtype=int)

        detections = []
        for i in range(len(xyxy)):
            detections.append({
                "box": xyxy[i],
                "class_id": int(class_ids[i]),
                "confidence": float(confidences[i]),
                "track_id": int(track_ids[i]),
            })
        return detections

app = Flask(__name__)
# Configuração do Banco SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chickguard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'chave-secreta-granja-segura'

CORS(app)
db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Cria tabelas ao iniciar
with app.app_context():
    db.create_all()
    # Cria admin se não existir
    if not User.query.filter_by(username='admin').first():
        hashed = bcrypt.generate_password_hash('admin123').decode('utf-8')
        db.session.add(User(username='admin', password=hashed))
        db.session.commit()

# --- VARIÁVEIS GLOBAIS ---
CAMERA_INDEX = 0 
global_frame = None
fps_last_time = 0
db_last_save_time = 0
lock = threading.Lock()
object_count = 0 # Variável para contagem de objetos
APP_START_TIME = time.time()
last_bird_snapshot_save_time = 0
live_birds = {}

# --- CONFIGURAÇÃO DA REDE NEURAL (YOLO) ---
# Instancia o detector de objetos
detector = ObjectDetector(model_path=YOLO_MODEL_PATH)

if detector.yolo_loaded:
    print("\n" + "="*60)
    print(f"Modelo: {YOLO_MODEL_PATH} | Tracker: {TRACKER_CONFIG} | Classe alvo: {BIRD_CLASS_NAME}")
    if MODO_DETECCAO == 'objetos':
        print("ℹ️  MODO DE TESTE ATIVADO: O sistema irá detetar objetos gerais.")
        print("   Aponte a câmara para um dos seguintes itens para testar:")
        test_objects = ['person', 'cell phone', 'bottle', 'cup', 'book', 'keyboard', 'mouse', 'tvmonitor', 'laptop']
        print(f"   ➡️  {', '.join(test_objects)}")
    else:
        print("✅ MODO DE PRODUÇÃO ATIVADO: O sistema irá detetar apenas 'aves'.")
    print("="*60 + "\n")

# Estado dos dispositivos (simulado)
def _estimate_bird_temp_proxy(gray_frame, box, ambient_temp):
    """
    Estimativa de temperatura por ave usando brilho local (proxy).
    Para temperatura individual real, use cÃ¢mera tÃ©rmica calibrada.
    """
    x1, y1, x2, y2 = box
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(gray_frame.shape[1], x2)
    y2 = min(gray_frame.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return round(float(ambient_temp), 2)

    roi = gray_frame[y1:y2, x1:x2]
    if roi.size == 0:
        return round(float(ambient_temp), 2)

    local_brightness = float(np.mean(roi))
    adjustment = ((local_brightness / 255.0) - 0.5) * 2.5
    return round(float(ambient_temp + adjustment), 2)


def _class_name_by_id(class_id):
    names = detector.model.names if detector and detector.model is not None else {}
    if isinstance(names, dict):
        return str(names.get(class_id, ""))
    if isinstance(names, list) and 0 <= class_id < len(names):
        return str(names[class_id])
    return ""


def _save_bird_snapshots(frame, ambient_temp):
    global last_bird_snapshot_save_time

    now = time.time()
    if now - last_bird_snapshot_save_time < BIRD_SNAPSHOT_SAVE_INTERVAL:
        return

    with lock:
        birds_items = list(live_birds.items())

    if not birds_items:
        last_bird_snapshot_save_time = now
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rows = []
    for bird_uid, data in birds_items:
        box = data["box"]
        est_temp = _estimate_bird_temp_proxy(gray, box, ambient_temp)
        rows.append(
            BirdSnapshot(
                bird_uid=int(bird_uid),
                confidence=float(data["conf"]),
                x1=int(box[0]),
                y1=int(box[1]),
                x2=int(box[2]),
                y2=int(box[3]),
                temperatura_estimada=est_temp,
                metodo_temperatura="estimada_rgb_proxy",
            )
        )

    if rows:
        with app.app_context():
            db.session.bulk_save_objects(rows)
            db.session.commit()

    last_bird_snapshot_save_time = now

estado_dispositivos = {
    "ventilacao": False,
    "aquecedor": False
}

# --- FUNÇÃO DE DETECÇÃO ---
def detectar_objetos(frame):
    global object_count, live_birds

    draw_frame = frame.copy()
    detections = detector.detect(draw_frame)

    frame_area = frame.shape[0] * frame.shape[1]
    min_bird_area = frame_area * MIN_BIRD_AREA_RATIO

    selected = []
    if MODO_DETECCAO == 'aves':
        target_name = BIRD_CLASS_NAME.strip().lower()
        for det in detections:
            class_name = _class_name_by_id(det["class_id"]).lower()
            if class_name != target_name:
                continue
            x1, y1, x2, y2 = det["box"]
            area = max(0, x2 - x1) * max(0, y2 - y1)
            if area < min_bird_area:
                continue
            selected.append(det)
    else:
        selected = detections

    now = time.time()
    with lock:
        if MODO_DETECCAO == 'aves':
            for det in selected:
                tid = int(det["track_id"])
                if tid < 0:
                    continue
                live_birds[tid] = {
                    "box": [int(v) for v in det["box"]],
                    "conf": float(det["confidence"]),
                    "last_seen": now,
                }

            stale = [tid for tid, info in live_birds.items() if (now - float(info["last_seen"])) > BIRD_LIVE_TTL_SEC]
            for tid in stale:
                live_birds.pop(tid, None)

            object_count = sum(1 for info in live_birds.values() if (now - float(info["last_seen"])) <= BIRD_LIVE_TTL_SEC)
        else:
            object_count = len(selected)

    if detector.yolo_loaded:
        print(f"[TRACKER] modo={MODO_DETECCAO} selecionadas={len(selected)} visiveis={object_count}")

    if detector.yolo_loaded:
        font = cv2.FONT_HERSHEY_PLAIN
        for det in selected:
            x1, y1, x2, y2 = det["box"]
            class_name = _class_name_by_id(det["class_id"]) or "obj"
            tid = int(det["track_id"])
            confidence = float(det["confidence"])
            color = (0, 255, 0)
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name} ID:{tid} ({confidence:.2f})" if tid >= 0 else f"{class_name} ({confidence:.2f})"
            cv2.putText(draw_frame, label, (x1, max(20, y1 - 5)), font, 1.3, color, 2)

    if object_count == 0 and detector.yolo_loaded:
        height, _, _ = frame.shape
        feedback_text = "IA ATIVA (NENHUMA AVE DETECTADA)" if MODO_DETECCAO == 'aves' else "IA ATIVA (NENHUM OBJETO DETECTADO)"
        cv2.putText(draw_frame, feedback_text, (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    font = cv2.FONT_HERSHEY_PLAIN
    if MODO_DETECCAO == 'aves':
        cv2.putText(draw_frame, f"Aves visiveis (IDs): {object_count}", (10, 30), font, 2, (0, 255, 0), 2)
    else:
        cv2.putText(draw_frame, f"Objetos: {object_count}", (10, 30), font, 2, (0, 255, 0), 2)

    cfg_text = f"tracker={TRACKER_CONFIG} imgsz={INFERENCE_IMGSZ} conf={DETECTION_CONF:.2f} classe={BIRD_CLASS_NAME}"
    cv2.putText(draw_frame, cfg_text, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    return draw_frame

# --- THREAD DE CÂMERA (COM GRAVAÇÃO AUTOMÁTICA) ---
def camera_loop():
    global global_frame, db_last_save_time, fps_last_time

    cap = None
    use_basic_simulation = False
    last_error_print_time = 0

    print("\n" + "="*70)
    print("🚀 INICIANDO PIPELINE DE VÍDEO PROFISSIONAL COM ULTRALYTICS YOLOv8 🚀")
    print("1. Procurando por câmera real...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if cap.isOpened():
        print("✅ Câmera real encontrada!")
        use_basic_simulation = False
        # Priorizamos qualidade para detectar aves mais distantes.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"   - Resolução da câmera definida para: {int(width)}x{int(height)}")
    else:
        print("❌ Câmera real não encontrada.")
        print("2. Ativando MODO DE TESTE AUTOMÁTICO com 'TEST_OBJECT'.")
        use_basic_simulation = True
            
    print("="*70 + "\n")

    frame_counter = 0
    while True:
        try:
            frame_counter += 1
            if use_basic_simulation:
                # Simulação básica (se tudo falhar)
                frame = np.zeros((480, 640, 3), dtype=np.uint8) # Usar a mesma resolução
                
                # Desenha um objeto falso para teste
                fake_object_x, fake_object_y, fake_object_w, fake_object_h = 200, 150, 150, 150
                label = "TEST_OBJECT"
                color = (0, 255, 0) # Verde
                font = cv2.FONT_HERSHEY_PLAIN
                
                cv2.rectangle(frame, (fake_object_x, fake_object_y), (fake_object_x + fake_object_w, fake_object_y + fake_object_h), color, 2)
                cv2.putText(frame, label, (fake_object_x, fake_object_y - 5), font, 2, color, 3)
                
                # Força a contagem para 1 no modo de teste
                with lock:
                    object_count = 1
                cv2.putText(frame, f"Objetos: {object_count}", (10, 30), font, 2, (0, 255, 0), 2)
                
                processed_frame = frame
                temp_atual = 28 + random.uniform(-5, 5)
            else:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Perda de sinal da câmera. Alternando para simulação de teste.")
                    use_basic_simulation = True
                    continue

                # Deteção de Objetos
                processed_frame = detectar_objetos(frame)

                # Simula temperatura a partir do brilho (se não for um sensor térmico real)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brilho = np.mean(gray)
                temp_atual = 20 + (brilho / 255) * 20
            
            new_time = time.time()
            # Calcula e exibe FPS
            # Evita divisão por zero no primeiro frame
            fps = 1 / (new_time - fps_last_time) if (new_time - fps_last_time) > 0 else 0
            fps_last_time = new_time

            # Adiciona um contador de frames e FPS ao vídeo para feedback visual
            cv2.putText(processed_frame, f"FPS: {int(fps)}", (processed_frame.shape[1] - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

            # Atualiza frame global
            with lock:
                global_frame = processed_frame

            if MODO_DETECCAO == 'aves' and not use_basic_simulation:
                _save_bird_snapshots(frame, temp_atual)

            # --- GRAVAR NO BANCO A CADA 30 SEGUNDOS ---
            current_time = time.time()
            if current_time - db_last_save_time > 30: # Intervalo de salvamento
                with app.app_context():
                    status = "NORMAL"
                    if temp_atual < 26: status = "FRIO"
                    elif temp_atual > 32: status = "CALOR"
                    
                    nova_leitura = Reading(temperatura=round(temp_atual, 1), status=status)
                    db.session.add(nova_leitura)
                    db.session.commit()
                    print(f"💾 Dados salvos: {temp_atual:.1f}°C")
                db_last_save_time = current_time
            
            # O sleep foi removido para permitir que o loop rode na velocidade máxima possível.
            # time.sleep(0.01)

        except Exception as e:
            # "CAIXA PRETA": Captura QUALQUER erro que aconteça na thread
            current_time = time.time()
            # Imprime o erro na consola apenas a cada 5 segundos para não sobrecarregar
            if current_time - last_error_print_time > 5:
                print("\n" + "!"*80)
                print(f"CRITICAL ERROR IN CAMERA THREAD: {e}")
                import traceback
                traceback.print_exc()
                print("A thread de vídeo encontrou um erro fatal. Verifique a mensagem acima.")
                print("!"*80 + "\n")
                last_error_print_time = current_time
            
            # Desenha um frame de erro para feedback visual imediato no vídeo
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "THREAD ERROR", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
            with lock:
                global_frame = error_frame
            time.sleep(1)

# Inicia thread
t = threading.Thread(target=camera_loop)
t.daemon = True
t.start()

# --- ROTAS DA API ---

@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        return jsonify(access_token=create_access_token(identity=username)), 200
    return jsonify({"msg": "Credenciais inválidas"}), 401

@app.route('/api/video')
def video_feed():
    def generate():
        while True:
            with lock:
                if global_frame is None:
                    time.sleep(0.1)
                    continue
                # O frame já vem processado da thread da câmera
                ret, buffer = cv2.imencode('.jpg', global_frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05) # Limita a taxa de envio para economizar recursos (~20 FPS)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status', methods=['GET'])
def get_status():
    # Pega a última leitura do banco para consistência
    ultima = Reading.query.order_by(Reading.id.desc()).first()
    if ultima:
        return jsonify({
            "temperatura": ultima.temperatura,
            "status": ultima.status,
            "cor": "red" if ultima.status == "CALOR" else "blue" if ultima.status == "FRIO" else "green",
            "mensagem": "Atenção necessária" if ultima.status != "NORMAL" else "Ambiente estável"
        })
    return jsonify({"temperatura": 0, "status": "INICIANDO", "cor": "gray", "mensagem": "..."})

@app.route('/api/history', methods=['GET'])
def get_history():
    # Retorna as últimas 10 leituras para o gráfico
    leituras = Reading.query.order_by(Reading.id.desc()).limit(10).all()
    return jsonify([l.to_dict() for l in reversed(leituras)]) # Inverte para cronológico

# --- NOVA ROTA PARA CONTAGEM ---
@app.route('/api/chick_count', methods=['GET'])
def get_chick_count():
    global object_count
    with lock:
        count = object_count
    return jsonify({"count": count})


@app.route('/api/birds/live', methods=['GET'])
def get_live_birds():
    now = time.time()
    with lock:
        items = [
            {
                "bird_uid": int(bid),
                "confidence": round(float(data["conf"]), 4),
                "bbox": data["box"],
                "last_seen_seconds": round(now - float(data["last_seen"]), 2),
            }
            for bid, data in live_birds.items()
            if (now - float(data["last_seen"])) <= BIRD_LIVE_TTL_SEC
        ]

    items.sort(key=lambda item: item["bird_uid"])
    return jsonify({
        "count": len(items),
        "ttl_seconds": BIRD_LIVE_TTL_SEC,
        "items": items,
    })


@app.route('/api/birds/history', methods=['GET'])
def get_birds_history():
    limit = request.args.get("limit", default=300, type=int)
    limit = max(1, min(limit, 5000))
    rows = BirdSnapshot.query.order_by(BirdSnapshot.id.desc()).limit(limit).all()
    return jsonify([row.to_dict() for row in reversed(rows)])

# --- ROTAS DE CONTROLE ---

@app.route('/api/ventilacao', methods=['POST'])
def controlar_ventilacao():
    """Liga ou desliga a ventilação"""
    data = request.get_json()
    estado = data.get('ligar', None)
    
    if estado is None:
        return jsonify({"msg": "Parâmetro 'ligar' é obrigatório"}), 400
    
    estado_dispositivos['ventilacao'] = bool(estado)
    return jsonify({
        "ventilacao": estado_dispositivos['ventilacao'],
        "msg": "Ventilação ligada" if estado_dispositivos['ventilacao'] else "Ventilação desligada"
    })

@app.route('/api/aquecedor', methods=['POST'])
def controlar_aquecedor():
    """Liga ou desliga o aquecedor"""
    data = request.get_json()
    estado = data.get('ligar', None)
    
    if estado is None:
        return jsonify({"msg": "Parâmetro 'ligar' é obrigatório"}), 400
    
    estado_dispositivos['aquecedor'] = bool(estado)
    return jsonify({
        "aquecedor": estado_dispositivos['aquecedor'],
        "msg": "Aquecedor ligado" if estado_dispositivos['aquecedor'] else "Aquecedor desligado"
    })

@app.route('/api/estado-dispositivos', methods=['GET'])
def get_estado_dispositivos():
    """Retorna o estado atual dos dispositivos"""
    return jsonify(estado_dispositivos)

@app.route('/api/health')
def health_check():
    """Verifica a saúde do sistema, incluindo a thread da câmera."""
    return jsonify({
        "status": "ok",
        "camera_thread_alive": t.is_alive()
    })

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Resumo consolidado para dashboards web/mobile."""
    ultima = Reading.query.order_by(Reading.id.desc()).first()
    recentes = Reading.query.order_by(Reading.id.desc()).limit(30).all()

    temperaturas = [item.temperatura for item in recentes]
    alertas = [item for item in recentes if item.status != "NORMAL"]

    now = time.time()
    with lock:
        count = object_count
        alive_count = sum(1 for info in live_birds.values() if (now - float(info["last_seen"])) <= BIRD_LIVE_TTL_SEC)

    return jsonify({
        "temperatura_atual": ultima.temperatura if ultima else 0,
        "status_atual": ultima.status if ultima else "INICIANDO",
        "media_temperatura": round(sum(temperaturas) / len(temperaturas), 1) if temperaturas else 0,
        "contagem_aves": count,
        "aves_vivas_individuais": alive_count,
        "metodo_temperatura_ave": "estimada_rgb_proxy",
        "tracker": TRACKER_CONFIG,
        "classe_ave": BIRD_CLASS_NAME,
        "dispositivos": estado_dispositivos,
        "total_alertas": len(alertas),
        "modo_deteccao": MODO_DETECCAO
    })

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Lista alertas recentes baseada no histórico de leituras."""
    recentes = Reading.query.order_by(Reading.id.desc()).limit(50).all()
    itens = []

    for item in recentes:
        if item.status == "NORMAL":
            continue
        nivel = "alto" if item.status == "CALOR" else "medio"
        itens.append({
            "id": item.id,
            "tipo": item.status,
            "nivel": nivel,
            "mensagem": f"Temperatura em estado {item.status}",
            "temperatura": item.temperatura,
            "hora": item.timestamp.strftime("%H:%M:%S"),
            "data": item.timestamp.strftime("%d/%m/%Y")
        })

    if estado_dispositivos.get("aquecedor") and estado_dispositivos.get("ventilacao"):
        itens.insert(0, {
            "id": "devices-state",
            "tipo": "DISPOSITIVOS",
            "nivel": "baixo",
            "mensagem": "Ventilação e aquecedor ligados ao mesmo tempo.",
            "temperatura": None,
            "hora": time.strftime("%H:%M:%S"),
            "data": time.strftime("%d/%m/%Y")
        })

    return jsonify(itens)

@app.route('/api/system-info', methods=['GET'])
def get_system_info():
    """Informações de runtime para aba de sistema."""
    uptime_seconds = int(time.time() - APP_START_TIME)
    return jsonify({
        "uptime_seconds": uptime_seconds,
        "camera_thread_alive": t.is_alive(),
        "modo_deteccao": MODO_DETECCAO,
        "yolo_loaded": detector.yolo_loaded,
        "tracker": TRACKER_CONFIG,
        "modelo_ia": YOLO_MODEL_PATH,
        "classe_ave": BIRD_CLASS_NAME,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "camera_index": CAMERA_INDEX
    })

if __name__ == '__main__':
    # Roda em todas as interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)



