"""
ChikGuard — Auto-Anotação com Roboflow AI Workflows
=====================================================
Utiliza a API de Serverless Workflows do Roboflow (general-segmentation-api / SAM3)
para rotular automaticamente imagens de pintinhos e gerar um dataset pronto no formato YOLO.

Uso:
  python backend/scripts/autolabel_with_roboflow.py \\
    --images-dir data/annotation_frames/ \\
    --output-dir data/dataset/ \\
    --classes Chick \\
    --api-key $ROBOFLOW_API_KEY \\
    --train-after
"""

import argparse
import base64
import json
import os
import random
import shutil
import sys
import time
import cv2
import requests
import subprocess
from typing import List, Dict, Any

ROBOFLOW_SERVERLESS_URL = "https://serverless.roboflow.com/{workspace}/workflows/{workflow_id}"

def encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def call_roboflow_workflow(
    image_path: str,
    api_key: str = os.environ.get("ROBOFLOW_API_KEY", ""),
    workspace: str = "nicolas-mandarino",
    workflow_id: str = "general-segmentation-api",
    target_class: str = "Chick"
) -> Dict[str, Any]:
    b64_img = encode_image_base64(image_path)
    url = ROBOFLOW_SERVERLESS_URL.format(workspace=workspace, workflow_id=workflow_id)
    
    payload = {
        "api_key": api_key,
        "inputs": {
            "image": {"type": "base64", "value": b64_img},
            "classes": [target_class]
        },
        "parameters": {
            "classes": [target_class]
        }
    }
    
    res = requests.post(url, json=payload, timeout=30)
    if res.status_code != 200:
        raise RuntimeError(f"Erro na API do Roboflow ({res.status_code}): {res.text[:200]}")
    
    return res.json()

def convert_predictions_to_yolo(
    predictions_data: Dict[str, Any],
    img_width: int,
    img_height: int,
    class_map: Dict[str, int]
) -> List[str]:
    yolo_lines = []
    
    # Navega na resposta da workflow do Roboflow
    outputs = predictions_data.get("outputs", [])
    if not outputs:
        return yolo_lines
        
    preds_container = outputs[0].get("predictions", {})
    preds_list = preds_container.get("predictions", [])
    
    for item in preds_list:
        cls_name = item.get("class", "Chick")
        cls_id = class_map.get(cls_name, 0)
        
        # Caso 1: Segmentação por polígonos
        points = item.get("points", [])
        if points:
            poly_coords = []
            for pt in points:
                norm_x = max(0.0, min(1.0, pt["x"] / img_width))
                norm_y = max(0.0, min(1.0, pt["y"] / img_height))
                poly_coords.extend([f"{norm_x:.6f}", f"{norm_y:.6f}"])
            line = f"{cls_id} " + " ".join(poly_coords)
            yolo_lines.append(line)
        # Caso 2: Bounding Box padrão
        elif "x" in item and "y" in item and "width" in item and "height" in item:
            x_center = item["x"] / img_width
            y_center = item["y"] / img_height
            w = item["width"] / img_width
            h = item["height"] / img_height
            line = f"{cls_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}"
            yolo_lines.append(line)
            
    return yolo_lines

def build_dataset_and_autolabel(
    images_dir: str,
    output_dir: str,
    api_key: str,
    workspace: str,
    workflow_id: str,
    classes: List[str],
    val_split: float = 0.2
):
    print(f"\n{"="*65}")
    print("  🐥 ChikGuard — Auto-Anotação via Roboflow AI Workflow")
    print(f"{"="*65}")
    print(f"  Diretório de Imagens : {images_dir}")
    print(f"  Diretório de Destino : {output_dir}")
    print(f"  Classes               : {classes}")
    print(f"  Workspace/Workflow    : {workspace}/{workflow_id}")
    print(f"{"="*65}\n")
    
    if not os.path.exists(images_dir):
        print(f"[ERRO] Diretório de imagens não encontrado: {images_dir}")
        sys.exit(1)
        
    image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not image_files:
        print(f"[ERRO] Nenhuma imagem JPG/PNG encontrada em: {images_dir}")
        sys.exit(1)
        
    print(f"📷 {len(image_files)} imagens encontradas para rotulagem automática.")
    
    # Estruturação de diretórios YOLO
    train_img_dir = os.path.join(output_dir, "train", "images")
    train_lbl_dir = os.path.join(output_dir, "train", "labels")
    val_img_dir = os.path.join(output_dir, "val", "images")
    val_lbl_dir = os.path.join(output_dir, "val", "labels")
    
    for d in [train_img_dir, train_lbl_dir, val_img_dir, val_lbl_dir]:
        os.makedirs(d, exist_ok=True)
        
    class_map = {cls_name: i for i, cls_name in enumerate(classes)}
    
    random.shuffle(image_files)
    n_val = int(len(image_files) * val_split)
    val_set = set(image_files[:n_val])
    
    success_count = 0
    total_annotations = 0
    
    for idx, fname in enumerate(image_files, 1):
        src_path = os.path.join(images_dir, fname)
        img = cv2.imread(src_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        
        is_val = fname in val_set
        target_img_dir = val_img_dir if is_val else train_img_dir
        target_lbl_dir = val_lbl_dir if is_val else train_lbl_dir
        
        lbl_fname = os.path.splitext(fname)[0] + ".txt"
        dest_img_path = os.path.join(target_img_dir, fname)
        dest_lbl_path = os.path.join(target_lbl_dir, lbl_fname)
        
        print(f"[{idx}/{len(image_files)}] Processando {fname} via Roboflow AI...", end=" ")
        
        try:
            res_data = call_roboflow_workflow(
                image_path=src_path,
                api_key=api_key,
                workspace=workspace,
                workflow_id=workflow_id,
                target_class=classes[0]
            )
            yolo_lines = convert_predictions_to_yolo(res_data, w, h, class_map)
            
            # Copia imagem para dataset
            shutil.copy(src_path, dest_img_path)
            
            # Salva rótulos
            with open(dest_lbl_path, "w", encoding="utf-8") as f:
                f.write("\n".join(yolo_lines))
                
            print(f"✅ ({len(yolo_lines)} detecções/máscaras)")
            success_count += 1
            total_annotations += len(yolo_lines)
        except Exception as e:
            print(f"❌ Erro: {e}")
            
        time.sleep(0.1) # Evita rate limit abrupto
        
    # Criar data.yaml
    data_yaml_path = os.path.join(output_dir, "data.yaml")
    yaml_content = f"""path: {os.path.abspath(output_dir)}
train: train/images
val: val/images

nc: {len(classes)}
names: {json.dumps(classes)}
"""
    with open(data_yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
        
    print(f"\n🎉 Processo de Auto-Anotação concluído!")
    print(f"  • Imagens rotuladas : {success_count}/{len(image_files)}")
    print(f"  • Objetos anotados  : {total_annotations}")
    print(f"  • Config do Dataset : {data_yaml_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-anotação de dataset via Roboflow AI Workflows")
    parser.add_argument("--images-dir", type=str, required=True, help="Pasta contendo imagens não anotadas")
    parser.add_argument("--output-dir", type=str, default="data/dataset", help="Pasta final do dataset YOLO")
    parser.add_argument("--api-key", type=str, default=os.environ.get("ROBOFLOW_API_KEY", ""), help="Chave API Roboflow")
    parser.add_argument("--workspace", type=str, default="nicolas-mandarino", help="Workspace Roboflow")
    parser.add_argument("--workflow-id", type=str, default="general-segmentation-api", help="ID do Workflow Roboflow")
    parser.add_argument("--classes", type=str, nargs="+", default=["Chick"], help="Classes a identificar")
    parser.add_argument("--train-after", action="store_true", help="Iniciar o treinamento do YOLO logo após rotular")

    args = parser.parse_args()
    
    build_dataset_and_autolabel(
        images_dir=args.images_dir,
        output_dir=args.output_dir,
        api_key=args.api_key,
        workspace=args.workspace,
        workflow_id=args.workflow_id,
        classes=args.classes
    )
    
    if args.train_after:
        print("\n🚀 Iniciando o Treinamento do Modelo YOLO no ChikGuard...")
        subprocess.run(["python", "backend/scripts/train_robust_vision.py", "--data", os.path.join(args.output_dir, 'data.yaml'), "--epochs", "100", "--export"], check=True)
