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
last_save_time = 0
lock = threading.Lock()
chick_count = 0 # Nova variável para contagem

# --- CONFIGURAÇÃO DA REDE NEURAL (YOLO) ---
# Constrói caminhos absolutos para os arquivos do YOLO para evitar erros de diretório
basedir = os.path.abspath(os.path.dirname(__file__))
weights_path = os.path.join(basedir, "yolo", "yolov3-tiny.weights")
config_path = os.path.join(basedir, "yolo", "yolov3-tiny.cfg")
names_path = os.path.join(basedir, "yolo", "coco.names")

try:
    net = cv2.dnn.readNet(weights_path, config_path)
    classes = []
    with open(names_path, "r") as f:
        classes = [line.strip() for line in f.readlines()]
    layer_names = net.getLayerNames()
    output_layers_indices = net.getUnconnectedOutLayers()
    if hasattr(output_layers_indices, 'flatten'):
        output_layers_indices = output_layers_indices.flatten()
    output_layers = [layer_names[i - 1] for i in output_layers_indices]
    yolo_loaded = True
    print("✅ Modelo YOLO carregado com sucesso.")
except (cv2.error, FileNotFoundError) as e:
    yolo_loaded = False
    print(f"⚠️ Erro ao carregar o modelo YOLO: {e}")
    print("   Certifique-se de que a pasta 'backend/yolo' existe e contém os arquivos 'yolov3-tiny.weights', 'yolov3-tiny.cfg' e 'coco.names'.")


# Estado dos dispositivos (simulado)
estado_dispositivos = {
    "ventilacao": False,
    "aquecedor": False
}

# --- FUNÇÃO DE DETECÇÃO ---
def detectar_aves(frame):
    global chick_count
    if not yolo_loaded:
        with lock:
            chick_count = 0
        return frame

    height, width, channels = frame.shape
    
    # Criar um blob da imagem para a entrada da rede
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    class_ids = []
    confidences = []
    boxes = []
    
    # Processar as saídas da rede
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            # A classe 'bird' no COCO é um bom substituto para 'chick'
            if confidence > 0.5 and classes[class_id] == "bird":
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                # Coordenadas do retângulo
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Aplicar Non-Max Suppression para remover caixas sobrepostas
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    
    current_chick_count = 0
    if indexes is not None:
        # Em algumas versões, indexes é um array 2D
        if hasattr(indexes, 'flatten'):
            indexes = indexes.flatten()
        current_chick_count = len(indexes)
        font = cv2.FONT_HERSHEY_PLAIN
        for i in indexes:
            x, y, w, h = boxes[i]
            color = (0, 255, 0) # Verde
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

    with lock:
        chick_count = current_chick_count

    # Desenhar a contagem no frame
    font = cv2.FONT_HERSHEY_PLAIN
    cv2.putText(frame, f"Aves: {chick_count}", (10, 30), font, 2, (0, 255, 0), 2)
    
    return frame

# --- THREAD DE CÂMERA (COM GRAVAÇÃO AUTOMÁTICA) ---
def camera_loop():
    global global_frame, last_save_time

    cap = None
    is_video_file = False
    use_basic_simulation = False

    # 1. Tenta abrir a câmera real
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("⚠️ Câmera real não encontrada. Tentando usar vídeo de simulação 'video_granja.mp4'.")
        # 2. Se falhar, tenta abrir o arquivo de vídeo
        video_path = os.path.join(basedir, 'video_granja.mp4')
        cap = cv2.VideoCapture(video_path)
        is_video_file = True
        if not cap.isOpened():
            print("❌ Vídeo de simulação não encontrado. Usando simulação básica (tela preta).")
            print("   Para um teste visual, execute 'python gerar_video.py' na pasta 'backend'.")
            use_basic_simulation = True
    else:
        print("✅ Câmera real encontrada.")
        # Configura resolução baixa para performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    while True:
        if use_basic_simulation:
            # Simulação básica (se tudo falhar)
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.putText(frame, "SIMULACAO", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            temp_atual = 28 + random.uniform(-5, 5)
        else:
            ret, frame = cap.read()
            if not ret:
                if is_video_file: # Se for um vídeo, reinicia do começo
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else: # Se for uma câmera real que falhou, usa simulação básica
                    print("❌ Perda de sinal da câmera. Alternando para simulação básica.")
                    use_basic_simulation = True
                    continue
            
            # Leitura real (estimada via brilho se for webcam comum)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brilho = np.mean(gray)
            temp_atual = 20 + (brilho / 255) * 20

        # --- DETECÇÃO DE AVES ---
        processed_frame = detectar_aves(frame.copy())

        # Atualiza frame global
        with lock:
            global_frame = processed_frame

        # --- GRAVAR NO BANCO A CADA 30 SEGUNDOS ---
        current_time = time.time()
        if current_time - last_save_time > 30: # Intervalo de salvamento
            with app.app_context():
                status = "NORMAL"
                if temp_atual < 26: status = "FRIO"
                elif temp_atual > 32: status = "CALOR"
                
                nova_leitura = Reading(temperatura=round(temp_atual, 1), status=status)
                db.session.add(nova_leitura)
                db.session.commit()
                print(f"💾 Dados salvos: {temp_atual:.1f}°C")
            last_save_time = current_time
            
        time.sleep(0.1)

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
    global chick_count
    with lock:
        count = chick_count
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

if __name__ == '__main__':
    # Roda em todas as interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)
