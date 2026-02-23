import cv2
import numpy as np
from collections import deque

class VideoProcessor:
    def __init__(self, video_path='video_granja.mp4'):
        """Inicializa o processador de vídeo"""
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.frame_count = 0
        self.current_frame = None
        self.frame_buffer = deque(maxlen=30)  # Buffer de 30 frames
        
        if not self.cap.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")
        
        print(f"✓ Vídeo carregado: {video_path}")
    
    def get_next_frame(self):
        """Lê o próximo frame do vídeo (com loop)"""
        ret, frame = self.cap.read()
        
        if not ret:
            # Reinicia do início
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        
        self.frame_count += 1
        self.current_frame = frame
        self.frame_buffer.append(frame.copy())
        return frame
    
    def detect_heat_blobs(self, frame):
        """
        Detecta aglomerações de calor (branco/cinza claro)
        Retorna contornos e centros
        """
        # Converte para grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Threshold para detectar áreas brancas/cinzas claras (calor)
        _, threshold = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Remove ruído
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
        threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
        
        # Encontra contornos
        contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        blobs = []
        for contour in contours:
            area = cv2.contourArea(contour)
            # Filtra apenas blobs significantes (mínimo 5 pixels, máximo 500)
            if 5 < area < 500:
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    blobs.append({
                        "x": cx,
                        "y": cy,
                        "area": area,
                        "contour": contour
                    })
        
        return blobs, threshold
    
    def calculate_density(self, blobs, frame_shape):
        """
        Calcula densidade de aves dividindo a tela em zonas
        Retorna temperatura estimada baseada na densidade
        """
        height, width = frame_shape[:2]
        
        # Divide em 9 zonas (3x3)
        zone_width = width // 3
        zone_height = height // 3
        
        zones = {}
        for i in range(3):
            for j in range(3):
                zone_key = f"zone_{i}_{j}"
                zones[zone_key] = {
                    "count": 0,
                    "density": 0,
                    "x": j * zone_width,
                    "y": i * zone_height
                }
        
        # Conta blobs por zona
        for blob in blobs:
            zone_i = min(blob["y"] // zone_height, 2)
            zone_j = min(blob["x"] // zone_width, 2)
            zone_key = f"zone_{zone_i}_{zone_j}"
            zones[zone_key]["count"] += 1
        
        # Calcula densidade
        max_density = 0
        for zone in zones.values():
            zone_area = zone_width * zone_height
            zone["density"] = (zone["count"] / zone_area) * 100
            max_density = max(max_density, zone["density"])
        
        return zones, len(blobs), max_density
    
    def estimate_temperature(self, density, total_blobs):
        """
        Estima temperatura baseada na densidade de aves
        - Muitas aves amontoadas = FRIO (densa)
        - Poucas aves espalhadas = CALOR (dispersa)
        """
        # Normaliza densidade (0-100)
        normalized_density = min(total_blobs / 10.0, 100)
        
        # Temperatura base 30°C com variação
        base_temp = 30.0
        
        # Se densidade alta (muitos blobs) = animais amontoados = frio
        # Se densidade baixa (poucos blobs) = animais espalhados = calor
        if total_blobs > 25:  # Amontoados
            temp = 25 + (normalized_density / 100) * 3  # 25-28°C
            status = "FRIO"
            color = "blue"
        elif total_blobs < 15:  # Espalhados
            temp = 34 + (normalized_density / 100) * 2  # 34-36°C
            status = "CALOR"
            color = "red"
        else:
            temp = base_temp + (normalized_density / 100) * 2
            status = "NORMAL"
            color = "green"
        
        return round(temp, 1), status, color
    
    def process_frame(self):
        """
        Processa um frame completo
        Retorna análise estruturada
        """
        frame = self.get_next_frame()
        blobs, threshold = self.detect_heat_blobs(frame)
        zones, total_blobs, max_density = self.calculate_density(blobs, frame.shape)
        temp, status, color = self.estimate_temperature(max_density, total_blobs)
        
        analysis = {
            "frame_id": self.frame_count,
            "temperatura": temp,
            "status": status,
            "cor": color,
            "total_aves_detectadas": total_blobs,
            "densidade_maxima": round(max_density, 2),
            "zonas": zones,
            "mensagem": self._generate_message(status, temp, total_blobs)
        }
        
        return analysis
    
    def _generate_message(self, status, temp, total_blobs):
        """Gera mensagem user-friendly"""
        messages = {
            "FRIO": f"🥶 FRIO! {total_blobs} aves amontoadas. Temp: {temp}°C. Ative o aquecedor!",
            "NORMAL": f"✓ NORMAL. {total_blobs} aves distribuídas. Temp: {temp}°C",
            "CALOR": f"🔥 CALOR! {total_blobs} aves fugindo para as bordas. Temp: {temp}°C. Ative ventilação!"
        }
        return messages.get(status, "Status desconhecido")
    
    def close(self):
        """Fecha o vídeo"""
        self.cap.release()
    
    def __del__(self):
        """Destrutor para garantir limpeza"""
        try:
            self.close()
        except:
            pass


# Instância global do processador
processor = None

def init_processor(video_path='video_granja.mp4'):
    """Inicializa o processador de vídeo"""
    global processor
    try:
        processor = VideoProcessor(video_path)
        return True
    except Exception as e:
        print(f"Erro ao inicializar processador: {e}")
        return False

def get_frame_analysis():
    """Retorna análise do próximo frame"""
    global processor
    if processor is None:
        return {"error": "Processador não inicializado"}
    
    try:
        return processor.process_frame()
    except Exception as e:
        print(f"Erro ao processar frame: {e}")
        return {"error": str(e)}
