"""
ChikGuard — Download de Dataset do Roboflow
=============================================
Este script baixa o seu dataset anotado no Roboflow e prepara no formato YOLOv8/YOLOv11.

Uso:
    python backend/scripts/download_roboflow.py --api-key SUAM_CHAVE_ROBOFLOW --workspace SEU_WORKSPACE --project SEU_PROJETO --version SEU_NUMERO_VERSAO
"""

import argparse
import os
import sys

def download_dataset(api_key: str, workspace: str, project: str, version: int, dest_dir: str = "data/dataset"):
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERRO] O pacote 'roboflow' não está instalado.")
        print("Instale com: pip install roboflow")
        sys.exit(1)

    print(f"🔄 Conectando ao Roboflow ({workspace}/{project} v{version})...")
    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    
    # Exporta e baixa no formato yolov8 (compatível com YOLOv8 e YOLOv11)
    dataset = proj.version(version).download("yolov8", location=os.path.abspath(dest_dir))
    
    print(f"\n✅ Dataset baixado com sucesso em: {dataset.location}")
    print(f"📄 Arquivo de configuração: {os.path.join(dataset.location, 'data.yaml')}")
    print("\n🚀 Próximo passo (Treinamento):")
    print(f"python backend/scripts/train_robust_vision.py --data {os.path.join(dataset.location, 'data.yaml')} --epochs 100")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baixar dataset anotado do Roboflow")
    parser.add_argument("--api-key", type=str, required=True, help="Chave de API do Roboflow")
    parser.add_argument("--workspace", type=str, required=True, help="Nome do workspace no Roboflow")
    parser.add_argument("--project", type=str, required=True, help="Nome do projeto no Roboflow")
    parser.add_argument("--version", type=int, default=1, help="Número da versão do export")
    parser.add_argument("--dest", type=str, default="data/dataset", help="Pasta de destino local")

    args = parser.parse_args()
    download_dataset(args.api_key, args.workspace, args.project, args.version, args.dest)
