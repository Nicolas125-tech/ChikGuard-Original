"""
ChikGuard - Script de Treinamento Robusto de Visão Computacional
================================================================
Este script implementa as diretrizes arquiteturais para treinar o YOLOv8-Seg 
(Segmentação de Instância) com foco em resiliência a ambientes adversos (poeira, 
oclusão densa, variação extrema de iluminação).

As augmentations agressivas configuradas garantem a identificação mesmo 
quando os pintinhos viram 'pontos amarelos' ao fundo.
"""

import os
from ultralytics import YOLO
import platform

def train_robust_model(data_yaml_path="dataset/data.yaml", epochs=300):
    print("=================================================================")
    print("🐓 ChikGuard - Iniciando Pipeline de Treinamento Robusto YOLOv8-Seg")
    print("=================================================================")
    
    # 1. Carregar modelo base State-of-the-art para Segmentação
    model = YOLO("yolov8n-seg.pt")
    print(f"Modelo base {model.ckpt_path} carregado. Tipologia: Segmentação de Instância")

    # 2. Configurar hiperparâmetros extremos para resiliência de Granja
    # (Adaptado para lidar com poeira, desfoque de movimento e oclusão de aves)
    train_args = {
        "data": data_yaml_path,
        "epochs": epochs,
        "imgsz": 640, # Resolução base, importante para o SAHI depois
        "batch": 16,
        "device": 0 if platform.system() != "Windows" else "", # Auto detect
        
        # Otimizadores e Aprendizado Dinâmico
        "optimizer": "auto",
        "lr0": 0.01,
        "lrf": 0.01,
        
        # =========================================================
        # ESTRATÉGIAS AGRESSIVAS DE MULTI-ESCALA E DATA AUGMENTATION
        # =========================================================
        
        # Múltiplas Escalas: Simula a câmera oscilando em zoom/distância
        "scale": 0.5,     
        
        # Oclusão e Densidade (Fundamental para milhares de pintinhos juntos)
        "mosaic": 1.0,      # Combina 4 imagens numa só (escala os objetos para 1/4 do tamanho, ótimo para pequenos objetos)
        "mixup": 0.2,       # Transparência entre as aves, simula oclusão forte
        "copy_paste": 0.1,  # Recorta aves e cola em outros lugares (só funciona bem porque estamos usando 'seg')
        
        # Simulação de Ponto de Vista da Câmera (Perspectiva)
        "degrees": 15.0,    # Câmera tremendo ou mal fixada
        "translate": 0.1,   
        
        # Simulação de Condições Adversas da Granja
        "hsv_h": 0.015,     # Variação de cor (Luz do Sol vs Lampadas Halógenas)
        "hsv_s": 0.7,       # Saturação (Pintinhos mais pálidos por poeira)
        "hsv_v": 0.4,       # Variação severa de Brilho (Zonas de Sombra dos Comedouros)
        
        # Desfoque por movimento (Aves ciscando rapidamente) e Poeira/Neblina no ar
        # Ultralytics suporta modificadores no albumentations se habilitado, 
        # mas estes básicos já fazem um bom trabalho de resiliência:
        "fliplr": 0.5,      # Inverte horizontalmente
        "bgr": 0.0,         # Não inverter canais RGB pois a cor amarela/marrom é importante
        
        # =========================================================
        "project": "runs/train",
        "name": "chikguard_robust_seg",
        "exist_ok": True
    }
    
    print("\nIniciando treinamento com os seguintes hiperparâmetros de resiliência:")
    for k, v in train_args.items():
        if k in ['mosaic', 'mixup', 'copy_paste', 'scale', 'hsv_h', 'hsv_s', 'hsv_v']:
            print(f"  --> {k}: {v} (Augmentation Robusta)")
        
    try:
        results = model.train(**train_args)
        print("\n✅ Treinamento robusto concluído com sucesso!")
        print(f"Pesos salvos em: {results.save_dir}")
        
    except Exception as e:
        print(f"\n❌ Erro durante o treinamento: {e}")
        print("Certifique-se de que o PyTorch está corretamente instalado com suporte a GPU.")

if __name__ == "__main__":
    # Exemplo de uso
    default_dataset = os.path.join(os.path.dirname(__file__), "..", "data", "dataset", "data.yaml")
    
    if not os.path.exists(default_dataset):
        print(f"Aviso: Dataset padrão não encontrado em {default_dataset}")
        print("Crie o dataset e o data.yaml antes de rodar o treinamento completo.")
        print("Saindo no modo de simulação...")
    else:
        train_robust_model(data_yaml_path=default_dataset)
