import argparse
from ultralytics import YOLO


def train(model_name, data_yaml, epochs, batch, imgsz, device):
    """
    Treina um modelo YOLOv8 ou YOLOv10 usando transfer learning.

    Args:
        model_name (str): Nome do modelo base (ex: yolov8n.pt, yolov10s.pt)
        data_yaml (str): Caminho para o arquivo data.yaml do dataset de avicultura
        epochs (int): Número de épocas de treinamento
        batch (int): Tamanho do batch
        imgsz (int): Tamanho da imagem
        device (str): Dispositivo de treinamento ('cpu', '0' para GPU)
    """
    print(f"Iniciando treinamento com o modelo base: {model_name}")
    print(f"Dataset: {data_yaml}")

    # Carregar modelo pré-treinado
    model = YOLO(model_name)

    # Iniciar treinamento
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        device=device,
        project='runs/train',
        name='avicultura_model',
        exist_ok=True,
        pretrained=True,  # Garantir uso de pesos pré-treinados
        optimizer='auto',
        verbose=True
    )

    print(f"Treinamento concluído. Modelo salvo em: {results.save_dir}")
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Script para treinamento de modelo YOLO para avicultura via Transfer Learning.")
    parser.add_argument(
        '--model',
        type=str,
        default='yolov8n.pt',
        help="Modelo base (ex: yolov8n.pt, yolov8s.pt, yolov10n.pt)")
    parser.add_argument(
        '--data',
        type=str,
        required=True,
        help="Caminho para o arquivo data.yaml do dataset")
    parser.add_argument(
        '--epochs',
        type=int,
        default=100,
        help="Número de épocas")
    parser.add_argument(
        '--batch',
        type=int,
        default=16,
        help="Tamanho do batch")
    parser.add_argument(
        '--imgsz',
        type=int,
        default=640,
        help="Tamanho da imagem para treinamento")
    parser.add_argument(
        '--device',
        type=str,
        default='cpu',
        help="Device ('cpu', '0', '0,1')")

    args = parser.parse_args()

    train(
        args.model,
        args.data,
        args.epochs,
        args.batch,
        args.imgsz,
        args.device)
