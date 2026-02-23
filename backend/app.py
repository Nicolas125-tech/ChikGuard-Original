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

# Estado dos dispositivos (simulado)
estado_dispositivos = {
    "ventilacao": False,
    "aquecedor": False
}

# --- THREAD DE CÂMERA (COM GRAVAÇÃO AUTOMÁTICA) ---
def camera_loop():
    global global_frame, last_save_time
    
    # Tenta abrir câmera real
    cap = cv2.VideoCapture(CAMERA_INDEX)
    # Configura resolução baixa para performance no Raspberry
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 256)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 192)
    
    using_simulation = not cap.isOpened()
    if using_simulation: print("⚠️ Câmera não encontrada. Usando Simulação.")

    while True:
        if using_simulation:
            # Simulação térmica
            frame = np.zeros((192, 256, 3), dtype=np.uint8)
            cv2.putText(frame, "SIMULACAO", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            # Adiciona ruído visual
            noise = np.random.randint(0, 50, (192, 256, 3), dtype=np.uint8)
            frame = cv2.add(frame, noise)
            
            # Simula temperatura
            temp_atual = 28 + random.uniform(-5, 5)
        else:
            ret, frame = cap.read()
            if not ret: 
                using_simulation = True
                continue
            
            # Leitura real (estimada via brilho se for webcam comum)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brilho = np.mean(gray)
            temp_atual = 20 + (brilho / 255) * 20

        # Atualiza frame global
        with lock:
            global_frame = frame

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
                # Aplica colormap se for simulação ou câmera P/B
                colored = cv2.applyColorMap(global_frame, cv2.COLORMAP_INFERNO)
                ret, buffer = cv2.imencode('.jpg', colored)
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
