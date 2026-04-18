"""
Script de Integração: SAHI + YOLO para Detecção de Pequenos Objetos (Pintinhos)
Este script demonstra como configurar o fatiamento de imagem para alta precisão em galpões.
"""

import cv2
import time
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
from sahi.utils.cv import read_image
from ultralytics import YOLO

def run_sahi_inference(image_path, model_path="yolov8n-seg.pt"):
    # 1. Carregar o Modelo através do Wrapper do SAHI
    detection_model = AutoDetectionModel.from_pretrained(
        model_type='ultralytics',
        model_path=model_path,
        confidence_threshold=0.3,
        device="cpu", # Alterar para 'cuda' se tiver GPU
    )

    # 2. Carregar Imagem
    image = read_image(image_path)

    # 3. Executar Inferência Fatiada (Sliced Inference)
    # slice_height/width: tamanho das fatias (ex: 320x320)
    # overlap: sobreposição entre fatias para evitar cortar aves no meio
    print("Iniciando inferência SAHI fatiada...")
    start_time = time.time()
    result = get_sliced_prediction(
        image,
        detection_model,
        slice_height=416,
        slice_width=416,
        overlap_height_ratio=0.2,
        overlap_width_ratio=0.2
    )
    end_time = time.time()

    # 4. Processar Resultados
    object_prediction_list = result.object_prediction_list
    print(f"Detecções finalizadas em {end_time - start_time:.2f}s")
    print(f"Total de aves encontradas: {len(object_prediction_list)}")

    # 5. Salvar/Visualizar
    # O SAHI pode exportar o frame com boxes desenhadas
    result.export_visuals(export_dir="backend/reports/sahi_outputs/")
    
    return result

if __name__ == "__main__":
    # Exemplo de uso
    import os
    sample_img = "backend/video_granja.mp4" # Na verdade é vídeo, mas SAHI pode ler frame
    # Para o exemplo, pegamos um frame do vídeo se necessário
    print("SAHI Integration Script ready. Configure os caminhos antes de rodar.")
