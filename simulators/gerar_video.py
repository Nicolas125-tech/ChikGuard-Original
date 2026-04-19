import cv2
import numpy as np
import random

# Configurações do Vídeo
WIDTH, HEIGHT = 640, 480
FPS = 30
DURATION_SEC = 30 # 10s Normal, 10s Frio, 10s Calor
OUTPUT_FILE = 'video_granja.mp4'

# --- ALTERAÇÃO: AUMENTANDO A POPULAÇÃO ---
NUM_PINTINHOS = 300 # Agora são 300 aves (Densidade alta)
pintinhos = []

for _ in range(NUM_PINTINHOS):
    pintinhos.append({
        "x": random.randint(50, WIDTH-50),
        "y": random.randint(50, HEIGHT-50),
        "vx": random.uniform(-2, 2),
        "vy": random.uniform(-2, 2)
    })

# Inicializa Gravador de Vídeo
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(OUTPUT_FILE, fourcc, FPS, (WIDTH, HEIGHT))

print(f"Gerando vídeo de ALTA DENSIDADE com EFEITO TÉRMICO '{OUTPUT_FILE}'... Aguarde.")

for frame_idx in range(FPS * DURATION_SEC):
    # 1. Cria uma matriz de CALOR (1 canal apenas, escala de cinza)
    # 0 = Frio Absoluto, 255 = Calor Máximo
    heatmap = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    
    # Define o comportamento baseado no tempo
    modo = "NORMAL"
    if 10 * FPS < frame_idx < 20 * FPS:
        modo = "FRIO" # Amontoar no centro
    elif frame_idx >= 20 * FPS:
        modo = "CALOR" # Fugir para as bordas

    for p in pintinhos:
        # Atualiza posição
        if modo == "NORMAL":
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0 or p["x"] > WIDTH: p["vx"] *= -1
            if p["y"] < 0 or p["y"] > HEIGHT: p["vy"] *= -1

        elif modo == "FRIO":
            dx = (WIDTH/2) - p["x"]
            dy = (HEIGHT/2) - p["y"]
            p["x"] += dx * 0.05 + random.uniform(-2, 2)
            p["y"] += dy * 0.05 + random.uniform(-2, 2)

        elif modo == "CALOR":
            dx = p["x"] - (WIDTH/2)
            dy = p["y"] - (HEIGHT/2)
            dist = max(1, (dx**2 + dy**2)**0.5)
            p["x"] += (dx/dist) * 4
            p["y"] += (dy/dist) * 4

        # --- DESENHA O CALOR NA MATRIZ ---
        # Em vez de cores, usamos INTENSIDADE (0-255)
        
        # Aura Térmica (Calor irradiado em volta do animal) - Intensidade Baixa (50)
        cv2.circle(heatmap, (int(p["x"]), int(p["y"])), 12, 50, -1) 
        
        # Corpo do animal - Intensidade Média (150)
        cv2.circle(heatmap, (int(p["x"]), int(p["y"])), 6, 150, -1) 
        
        # Núcleo do corpo - Intensidade Máxima (255)
        cv2.circle(heatmap, (int(p["x"]), int(p["y"])), 3, 255, -1)

    # 2. Aplica Blur para simular a dispersão de calor e baixa resolução do sensor
    # Isso faz as "auras" se fundirem quando eles se juntam
    heatmap = cv2.GaussianBlur(heatmap, (25, 25), 0)
    
    # 3. A MÁGICA: Aplica o Colormap (Transforma Cinza em Cores Térmicas)
    # COLORMAP_JET cria o efeito clássico (Azul -> Verde -> Amarelo -> Vermelho)
    frame_colorido = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    
    # Escreve texto de debug (Branco para contrastar)
    cv2.putText(frame_colorido, f"Modo: {modo}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame_colorido, "Simulacao Termica AI", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    out.write(frame_colorido)

out.release()
print("Vídeo térmico gerado com sucesso!")
