"""
ChikGuard — Download de Dataset do Roboflow (Poultry Detection)
================================================================
Baixa o dataset anotado 'poultry-detection-mqriw-fzt08' do Roboflow.

Uso:
    python backend/scripts/download_roboflow.py
"""

import argparse
import os
import sys

DEFAULT_API_KEY = "OiHV8fQKPBECkIpTGXb5"
DEFAULT_WORKSPACE = "nicolas-mandarino"
DEFAULT_PROJECT = "poultry-detection-mqriw-fzt08"
DEFAULT_VERSION = 1

def download_dataset(
    api_key: str = DEFAULT_API_KEY,
    workspace: str = DEFAULT_WORKSPACE,
    project: str = DEFAULT_PROJECT,
    version: int = DEFAULT_VERSION,
    format_type: str = "yolov8",
    dest_dir: str = "data/dataset"
):
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERRO] O pacote 'roboflow' não está instalado.")
        print("Instale com: pip install roboflow")
        sys.exit(1)

    print(f"🔄 Conectando ao Roboflow ({workspace}/{project} v{version})...")
    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    
    dataset_location = os.path.abspath(dest_dir)
    print(f"📥 Baixando dataset no formato '{format_type}' para: {dataset_location}")
    dataset = proj.version(version).download(format_type, location=dataset_location)
    
    data_yaml = os.path.join(dataset.location, "data.yaml")
    print(f"\n✅ Dataset baixado com sucesso em: {dataset.location}")
    print(f"📄 Configuração: {data_yaml}")
    print("\n🚀 Treinando o modelo no ChikGuard com o novo dataset...")
    
    return data_yaml

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baixar dataset anotado do Roboflow")
    parser.add_argument("--api-key", type=str, default=DEFAULT_API_KEY, help="Chave de API do Roboflow")
    parser.add_argument("--workspace", type=str, default=DEFAULT_WORKSPACE, help="Nome do workspace no Roboflow")
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT, help="Nome do projeto no Roboflow")
    parser.add_argument("--version", type=int, default=DEFAULT_VERSION, help="Número da versão do export")
    parser.add_argument("--format", type=str, default="yolov8", help="Formato do export (yolov8, yolov8-obb, etc)")
    parser.add_argument("--dest", type=str, default="data/dataset", help="Pasta de destino local")

    args = parser.parse_args()
    download_dataset(args.api_key, args.workspace, args.project, args.version, args.format, args.dest)
