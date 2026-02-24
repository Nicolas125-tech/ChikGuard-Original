from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from database import db, User, Reading # Importar Reading
import cv2
import numpy as np
import threading
import time
import os
import random

class ObjectDetector:
    """
    Encapsula a lógica de deteção de objetos YOLO para uma melhor organização e robustez.
    """
    def __init__(self, weights_path, config_path, names_path):
        self.yolo_loaded = False
        self.classes = []
        try:
            self.net = cv2.dnn.readNet(weights_path, config_path)
            with open(names_path, "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            layer_names = self.net.getLayerNames()
            output_layers_indices = self.net.getUnconnectedOutLayers()
            if hasattr(output_layers_indices, 'flatten'):
                output_layers_indices = output_layers_indices.flatten()
            
            self.output_layers = [layer_names[i - 1] for i in output_layers_indices]
            self.yolo_loaded = True
            print("✅ Modelo YOLO carregado com sucesso para a classe ObjectDetector.")
        except (cv2.error, FileNotFoundError) as e:
            print(f"⚠️ Erro ao carregar o modelo YOLO na classe ObjectDetector: {e}")
            print("   Certifique-se de que a pasta 'backend/yolo' existe e contém os arquivos necessários.")

    def detect(self, frame, confidence_threshold=0.4, nms_threshold=0.4):
        if not self.yolo_loaded:
            return [], [], []

        height, width, _ = frame.shape
        # A rede YOLOv3-tiny foi treinada com imagens 416x416
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

        class_ids = []
        confidences = []
        boxes = []

        raw_detections_count = 0
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > confidence_threshold:
                    raw_detections_count += 1
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # Log para diagnóstico: mostra quantas detecções brutas foram encontradas
        print(f"[DETECTOR] Deteções brutas (conf > {confidence_threshold}): {raw_detections_count}")
        
        # Aplica Non-Max Suppression para refinar as caixas de deteção
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold)

        if indexes is not None:
            if hasattr(indexes, 'flatten'):
                indexes = indexes.flatten()
            # Retorna apenas os resultados filtrados pelo NMS
            return [boxes[i] for i in indexes], [class_ids[i] for i in indexes], [confidences[i] for i in indexes]

        return [], [], []

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

# --- CONFIGURAÇÃO DA REDE NEURAL (YOLO) ---
basedir = os.path.abspath(os.path.dirname(__file__))
weights_path = os.path.join(basedir, "yolo", "yolov3-tiny.weights")
config_path = os.path.join(basedir, "yolo", "yolov3-tiny.cfg")
names_path = os.path.join(basedir, "yolo", "coco.names")

# Instancia o detector de objetos
detector = ObjectDetector(weights_path, config_path, names_path)

if detector.yolo_loaded:
    print("\n" + "="*60)
    print("ℹ️  MODO DE TESTE ATIVADO: O sistema irá detetar objetos gerais.")
    print("   Aponte a câmara para um dos seguintes itens para testar:")
    test_objects = ['person', 'cell phone', 'bottle', 'cup', 'book', 'keyboard', 'mouse', 'tvmonitor', 'laptop']
    print(f"   ➡️  {', '.join(test_objects)}")
    print("="*60 + "\n")

# Estado dos dispositivos (simulado)
estado_dispositivos = {
    "ventilacao": False,
    "aquecedor": False
}

# --- FUNÇÃO DE DETECÇÃO ---
def detectar_objetos(frame):
    global object_count
    
    # Copia o frame para não desenhar sobre o original que pode ser usado em outro lugar
    draw_frame = frame.copy()

    # Usa o detector para encontrar objetos. O limiar de confiança foi reduzido para 0.4 para ser mais permissivo.
    # Aumentamos o limiar de confiança de volta para 0.5 para reduzir falsos positivos.
    boxes, class_ids, confidences = detector.detect(draw_frame, confidence_threshold=0.5, nms_threshold=0.4)
    
    if detector.yolo_loaded:
        print(f"[DETECTOR] Objetos finais encontrados: {len(boxes)}")

    with lock:
        object_count = len(boxes)

    # Desenha as caixas e os rótulos no frame
    if detector.yolo_loaded:
        font = cv2.FONT_HERSHEY_PLAIN
        for i in range(len(boxes)):
            x, y, w, h = boxes[i]
            label = str(detector.classes[class_ids[i]])
            confidence = confidences[i]
            color = (0, 255, 0) # Verde
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            # Exibe o rótulo e a confiança para melhor diagnóstico
            text = f"{label} ({confidence:.2f})"
            cv2.putText(frame, text, (x, y - 5), font, 1.5, color, 2)

    # --- DIAGNOSTIC FEEDBACK ---
    if object_count == 0 and detector.yolo_loaded:
        height, _, _ = frame.shape
        # Adiciona texto no canto inferior para feedback constante
        cv2.putText(draw_frame, "IA ATIVA (NENHUM OBJETO DETECTADO)", (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # Desenhar a contagem no frame
    font = cv2.FONT_HERSHEY_PLAIN
    cv2.putText(draw_frame, f"Objetos: {object_count}", (10, 30), font, 2, (0, 255, 0), 2)
    
    return draw_frame

# --- THREAD DE CÂMERA (COM GRAVAÇÃO AUTOMÁTICA) ---
def camera_loop():
    global global_frame, db_last_save_time, fps_last_time

    cap = None
    use_basic_simulation = False
    last_error_print_time = 0

    print("\n" + "="*60)
    print("🚀 INICIANDO PIPELINE DE VÍDEO PROFISSIONAL 🚀")
    print("1. Procurando por câmera real...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if cap.isOpened():
        print("✅ Câmera real encontrada!")
        use_basic_simulation = False
        # AUMENTANDO A RESOLUÇÃO PARA MELHORAR A DETECÇÃO
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"   - Resolução da câmera definida para: {int(width)}x{int(height)}")
    else:
        print("❌ Câmera real não encontrada.")
        print("2. Ativando MODO DE TESTE AUTOMÁTICO com 'TEST_OBJECT'.")
        use_basic_simulation = True
            
    print("="*60 + "\n")

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

                # --- PIPELINE DE PROCESSAMENTO ---
                # 1. Overlay de Diagnóstico (Indiscutível)
                # Se isto não aparecer, o problema é na captura de vídeo ou no streaming.
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                cv2.circle(frame, (frame.shape[1] - 30, 30), 10, (0, 0, 255), -1) # Círculo vermelho no canto superior direito

                # 2. Deteção de Objetos
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
                
            time.sleep(0.01)

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
                if global_frame is None: continue
                # O frame já vem processado da thread da câmera
                ret, buffer = cv2.imencode('.jpg', global_frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
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

if __name__ == '__main__':
    # Roda em todas as interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)
