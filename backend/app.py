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
from ultralytics import YOLO # Importação da IA Profissional

# ======================================================================================
# --- CONFIGURAÇÃO DE DETECÇÃO ---
# Mude para 'aves' para o modo de produção ou 'objetos' para teste geral.
MODO_DETECCAO = 'aves'
# ======================================================================================

class ObjectDetector:
    """
    Encapsula a lógica de deteção de objetos usando a biblioteca Ultralytics.
    Esta abordagem é mais moderna, eficiente e precisa que a implementação com OpenCV DNN.
    """
    def __init__(self, model_path='yolov8n.pt'): # YOLOv8 Nano é pequeno, rápido e eficiente.
        self.yolo_loaded = False
        self.model = None
        try:
            # Carrega o modelo. A Ultralytics faz o download automático na primeira vez.
            self.model = YOLO(model_path)
            self.yolo_loaded = True
            print(f"✅ Modelo Ultralytics '{model_path}' carregado com sucesso.")
            # Aquece o modelo para a primeira inferência ser mais rápida
            self.model.predict(np.zeros((480, 640, 3)), verbose=False)
            print("✅ Modelo aquecido e pronto para uso.")
        except Exception as e:
            print(f"⚠️ Erro ao carregar o modelo Ultralytics: {e}")
            print("   Verifique sua conexão com a internet para o download do modelo ou o caminho do arquivo.")

    def detect(self, frame):
        if not self.yolo_loaded:
            return [], [], []

        # Realiza a predição. `verbose=False` para não poluir a consola.
        # Otimização: Definimos um tamanho de imagem menor (imgsz=320) para acelerar a inferência.
        results = self.model.predict(frame, verbose=False, conf=0.5, imgsz=320)
        result = results[0] # Pega os resultados do primeiro frame

        # Extrai as informações necessárias
        # Bounding boxes no formato (x1, y1, x2, y2)
        boxes = result.boxes.xyxy.cpu().numpy().astype(int) 
        class_ids = result.boxes.cls.cpu().numpy().astype(int)
        confidences = result.boxes.conf.cpu().numpy()
        
        return boxes, class_ids, confidences

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

# --- CONFIGURAÇÃO DA REDE NEURAL (YOLO) ---
# Instancia o detector de objetos
detector = ObjectDetector()

if detector.yolo_loaded:
    print("\n" + "="*60)
    if MODO_DETECCAO == 'objetos':
        print("ℹ️  MODO DE TESTE ATIVADO: O sistema irá detetar objetos gerais.")
        print("   Aponte a câmara para um dos seguintes itens para testar:")
        test_objects = ['person', 'cell phone', 'bottle', 'cup', 'book', 'keyboard', 'mouse', 'tvmonitor', 'laptop']
        print(f"   ➡️  {', '.join(test_objects)}")
    else:
        print("✅ MODO DE PRODUÇÃO ATIVADO: O sistema irá detetar apenas 'aves'.")
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
    # A confiança já é filtrada dentro do método `detect` da Ultralytics.
    boxes, class_ids, confidences = detector.detect(draw_frame)
    
    # --- FILTRAGEM BASEADA NO MODO ---
    filtered_boxes = []
    filtered_class_ids = []
    filtered_confidences = []

    if MODO_DETECCAO == 'aves':
        for i in range(len(class_ids)):
            # A classe 'bird' no dataset COCO é o que procuramos.
            if detector.model.names[class_ids[i]] == 'bird':
                filtered_boxes.append(boxes[i])
                filtered_class_ids.append(class_ids[i])
                filtered_confidences.append(confidences[i])
    else: # modo 'objetos'
        filtered_boxes = boxes
        filtered_class_ids = class_ids
        filtered_confidences = confidences

    if detector.yolo_loaded:
        print(f"[DETECTOR] Itens '{MODO_DETECCAO}' encontrados: {len(filtered_boxes)}")

    with lock:
        object_count = len(filtered_boxes)

    # Desenha as caixas e os rótulos no frame
    if detector.yolo_loaded:
        font = cv2.FONT_HERSHEY_PLAIN
        for i in range(len(filtered_boxes)):
            x1, y1, x2, y2 = filtered_boxes[i]
            label = str(detector.model.names[filtered_class_ids[i]])
            confidence = filtered_confidences[i]
            color = (0, 255, 0) # Verde
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), color, 2)
            # Exibe o rótulo e a confiança para melhor diagnóstico
            text = f"{label} ({confidence:.2f})"
            cv2.putText(draw_frame, text, (x1, y1 - 5), font, 1.5, color, 2)

    # --- DIAGNOSTIC FEEDBACK ---
    if object_count == 0 and detector.yolo_loaded:
        height, _, _ = frame.shape
        feedback_text = "IA ATIVA (NENHUMA AVE DETECTADA)" if MODO_DETECCAO == 'aves' else "IA ATIVA (NENHUM OBJETO DETECTADO)"
        # Adiciona texto no canto inferior para feedback constante
        cv2.putText(draw_frame, feedback_text, (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # Desenhar a contagem no frame
    font = cv2.FONT_HERSHEY_PLAIN
    label_text = "Aves" if MODO_DETECCAO == 'aves' else "Objetos"
    cv2.putText(draw_frame, f"{label_text}: {object_count}", (10, 30), font, 2, (0, 255, 0), 2)
    
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
        # Otimização: Reduzimos a resolução da captura para aumentar o FPS.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
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

    with lock:
        count = object_count

    return jsonify({
        "temperatura_atual": ultima.temperatura if ultima else 0,
        "status_atual": ultima.status if ultima else "INICIANDO",
        "media_temperatura": round(sum(temperaturas) / len(temperaturas), 1) if temperaturas else 0,
        "contagem_aves": count,
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
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "camera_index": CAMERA_INDEX
    })

if __name__ == '__main__':
    # Roda em todas as interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)
