import argparse
from ultralytics import YOLO


def export_model(weights_path, format_type, half, int8):
    """
    Exporta modelo YOLO para formatos otimizados para Edge Computing (OpenVINO, TensorRT).

    Args:
        weights_path (str): Caminho para os pesos do modelo (ex: runs/train/avicultura_model/weights/best.pt)
        format_type (str): Formato de saída ('openvino', 'engine')
        half (bool): Quantização FP16
        int8 (bool): Quantização INT8
    """
    print(f"Carregando modelo: {weights_path}")
    model = YOLO(weights_path)

    print(f"Iniciando exportação para formato: {format_type}")
    if half:
        print("Aviso: Aplicando quantização FP16")
    if int8:
        print("Aviso: Aplicando quantização INT8")

    try:
        exported_path = model.export(
            format=format_type,
            half=half,
            int8=int8,
            # OpenVINO usually exported on CPU, TensorRT on GPU
            device='cpu' if format_type == 'openvino' else '0'
        )
        print(f"Exportação concluída com sucesso. Salvo em: {exported_path}")
    except Exception as e:
        print(f"Erro durante a exportação: {str(e)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Script para exportar modelos YOLO para Edge Computing (OpenVINO/TensorRT) com quantização.")
    parser.add_argument(
        '--weights',
        type=str,
        required=True,
        help="Caminho para os pesos .pt do modelo")
    parser.add_argument(
        '--format',
        type=str,
        choices=[
            'openvino',
            'engine'],
        required=True,
        help="Formato de exportação (openvino para .xml, engine para TensorRT)")
    parser.add_argument(
        '--fp16',
        action='store_true',
        help="Habilitar quantização FP16 (Half precision)")
    parser.add_argument(
        '--int8',
        action='store_true',
        help="Habilitar quantização INT8")

    args = parser.parse_args()

    # Validações
    if args.int8 and args.fp16:
        print("Aviso: Ambas as opções FP16 e INT8 selecionadas. Verifique a documentação.")

    if args.format == 'engine' and not args.fp16 and not args.int8:
        print("Aviso: TensorRT sem quantização pode não ter a performance esperada.")

    export_model(args.weights, args.format, args.fp16, args.int8)
