"""
ChikGuard — Conversão de Modelo para OpenVINO (Intel Edge)
===========================================================
Converte YOLOv8n-Seg (.pt) para o formato OpenVINO IR (.xml/.bin)
com quantização FP16 (recomendado) ou INT8 (máxima velocidade).

Uso:
  # FP16 (recomendado para iGPU Intel - melhor balance precisão/velocidade)
  python scripts/convert_to_openvino.py --model yolov8n-seg.pt --precision FP16

  # INT8 (máxima velocidade, requer dataset de calibração)
  python scripts/convert_to_openvino.py \\
    --model yolov8n-seg.pt \\
    --precision INT8 \\
    --calibration-dir data/calibration/

Resultado:
  models/chikguard_seg_fp16_openvino/
  ├── model.xml     ← grafo da rede
  ├── model.bin     ← pesos quantizados
  └── metadata.yaml ← configuração para carregamento

Pós-conversão, configure o .env:
  INFERENCE_BACKEND=openvino
  OPENVINO_MODEL_XML=models/chikguard_seg_fp16_openvino/model.xml
"""

import argparse
import os
import sys
import time
import glob
import shutil

# ── Validação de dependências ──────────────────────────────────────────────────
def _check_deps():
    missing = []
    try:
        from ultralytics import YOLO
    except ImportError:
        missing.append("ultralytics")
    try:
        import openvino
    except ImportError:
        missing.append("openvino")
    if missing:
        print(f"[ERRO] Dependências em falta: {', '.join(missing)}")
        print("Instale com: pip install " + " ".join(missing))
        sys.exit(1)

_check_deps()

from ultralytics import YOLO
import yaml


def export_to_openvino(
    model_path: str,
    output_dir: str,
    precision: str = "FP16",
    imgsz: int = 640,
) -> str:
    """
    Etapa 1: Exporta o modelo .pt para OpenVINO via Ultralytics.
    Retorna o caminho para o diretório OpenVINO gerado.
    """
    print(f"\n{'='*60}")
    print(f"  ChikGuard — Exportação para OpenVINO {precision}")
    print(f"{'='*60}")
    print(f"  Modelo fonte : {model_path}")
    print(f"  Precisão     : {precision}")
    print(f"  Tamanho img  : {imgsz}px")

    if not os.path.exists(model_path):
        print(f"\n[ERRO] Arquivo não encontrado: {model_path}")
        sys.exit(1)

    model = YOLO(model_path)

    print(f"\n[1/3] Exportando para ONNX intermediário...")
    t0 = time.time()
    model.export(
        format="openvino",
        imgsz=imgsz,
        half=(precision.upper() == "FP16"),   # FP16 se half=True
        dynamic=False,                          # Static shapes = mais rápido no edge
    )
    elapsed = time.time() - t0

    # Ultralytics cria o diretório ao lado do modelo .pt
    auto_dir = model_path.replace(".pt", "_openvino_model")
    if not os.path.isdir(auto_dir):
        print(f"\n[ERRO] Diretório OpenVINO não encontrado após export: {auto_dir}")
        sys.exit(1)

    print(f"[1/3] ✅ Export concluído em {elapsed:.1f}s → {auto_dir}")
    return auto_dir


def quantize_int8(openvino_dir: str, calibration_dir: str, imgsz: int = 640) -> str:
    """
    Etapa 2 (opcional): Quantização INT8 usando NNCF + OpenVINO Post-Training Quantization.
    Requer dataset de calibração (imagens de granjas, sem anotações).
    """
    print(f"\n[2/3] Iniciando quantização INT8 com NNCF...")
    print(f"      Calibração via: {calibration_dir}")

    try:
        import openvino as ov
        import nncf                                                   # type: ignore
        from nncf.parameters import ModelType                         # type: ignore
        from openvino.runtime import Core                             # type: ignore
    except ImportError as e:
        print(f"\n[AVISO] NNCF não instalado ({e}). Pulando quantização INT8.")
        print("        Instale com: pip install nncf")
        return openvino_dir

    xml_path = os.path.join(openvino_dir, "model.xml")
    if not os.path.exists(xml_path):
        print(f"[AVISO] model.xml não encontrado em {openvino_dir}. Pulando INT8.")
        return openvino_dir

    import cv2
    import numpy as np

    # Carrega imagens de calibração
    patterns   = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    image_paths = []
    for pat in patterns:
        image_paths.extend(glob.glob(os.path.join(calibration_dir, pat)))

    if not image_paths:
        print(f"[AVISO] Nenhuma imagem de calibração em '{calibration_dir}'. Pulando INT8.")
        return openvino_dir

    print(f"      Imagens de calibração: {len(image_paths)}")

    def _calibration_dataset():
        for img_path in image_paths[:200]:   # máx 200 imagens
            img = cv2.imread(img_path)
            if img is None:
                continue
            img = cv2.resize(img, (imgsz, imgsz))
            img = img[:, :, ::-1].astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))
            yield {"images": np.expand_dims(img, 0)}

    core  = Core()
    model = core.read_model(xml_path)

    int8_model = nncf.quantize(
        model,
        nncf.Dataset(_calibration_dataset()),
        model_type=ModelType.TRANSFORMER,
        preset=nncf.QuantizationPreset.PERFORMANCE,
    )

    int8_dir = openvino_dir.replace("_openvino_model", "_openvino_int8")
    os.makedirs(int8_dir, exist_ok=True)
    out_xml = os.path.join(int8_dir, "model.xml")
    ov.save_model(int8_model, out_xml)
    print(f"[2/3] ✅ Modelo INT8 salvo em: {int8_dir}")
    return int8_dir


def copy_and_generate_metadata(
    src_dir: str,
    output_dir: str,
    model_path: str,
    precision: str,
    imgsz: int,
    class_names: list,
):
    """Copia o modelo para o diretório de saída e gera metadata.yaml."""
    print(f"\n[3/3] Copiando para destino final: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    for f in os.listdir(src_dir):
        shutil.copy2(os.path.join(src_dir, f), os.path.join(output_dir, f))

    # Gera metadata.yaml para o detector carregar automaticamente
    metadata = {
        "model_source":  model_path,
        "precision":     precision,
        "imgsz":         imgsz,
        "class_names":   class_names,
        "framework":     "OpenVINO",
        "sahi_slice":    640,
        "sahi_overlap":  0.20,
        "conf_threshold": 0.25,
        "export_time":   time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(os.path.join(output_dir, "metadata.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(metadata, f, allow_unicode=True)

    print(f"[3/3] ✅ Modelo pronto em: {output_dir}")
    print(f"\n{'='*60}")
    print(f"  📋 PRÓXIMOS PASSOS:")
    print(f"")
    print(f"  1. Abra o arquivo .env e configure:")
    print(f"     INFERENCE_BACKEND=openvino")
    print(f"     OPENVINO_MODEL_XML={os.path.join(output_dir, 'model.xml')}")
    print(f"     ENABLE_SAHI=true")
    print(f"     SAHI_SLICE_SIZE=640")
    print(f"     SAHI_OVERLAP=0.20")
    print(f"     SAHI_WORKERS=4")
    print(f"     DETECTION_CONF=0.25")
    print(f"")
    print(f"  2. Reinicie o servidor: python app.py")
    print(f"{'='*60}\n")


def benchmark_model(xml_path: str, imgsz: int = 640, n_runs: int = 50):
    """Roda benchmark de latência/FPS no modelo OpenVINO."""
    try:
        from openvino.runtime import Core
        import numpy as np
    except ImportError:
        print("[AVISO] OpenVINO não instalado, pulando benchmark.")
        return

    print(f"\n[BENCHMARK] Testando {n_runs} inferências @ {imgsz}px...")
    core   = Core()
    device = "GPU" if "GPU" in core.available_devices else "CPU"
    model  = core.compile_model(core.read_model(xml_path), device)

    dummy = np.random.rand(1, 3, imgsz, imgsz).astype(np.float32)
    input_key = model.input(0)

    # Warm-up
    for _ in range(5):
        model({input_key: dummy})

    t0 = time.perf_counter()
    for _ in range(n_runs):
        model({input_key: dummy})
    elapsed = time.perf_counter() - t0

    fps     = n_runs / elapsed
    lat_ms  = (elapsed / n_runs) * 1000

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │  BENCHMARK OpenVINO ({device:6s})        │")
    print(f"  │  Latência : {lat_ms:6.1f} ms / frame      │")
    print(f"  │  FPS      : {fps:6.1f} FPS              │")
    print(f"  │  Throughput SAHI (8 tiles) : {fps/8:5.1f} fps  │")
    print(f"  └─────────────────────────────────────┘\n")


def main():
    parser = argparse.ArgumentParser(
        description="Converte modelo YOLOv8-Seg para OpenVINO FP16/INT8"
    )
    parser.add_argument(
        "--model",
        default="yolov8n-seg.pt",
        help="Caminho para o modelo .pt (padrão: yolov8n-seg.pt)"
    )
    parser.add_argument(
        "--output",
        default="",
        help="Diretório de saída (padrão: models/<nome>_openvino_fp16/)"
    )
    parser.add_argument(
        "--precision",
        choices=["FP16", "INT8"],
        default="FP16",
        help="Precisão de quantização (padrão: FP16)"
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Tamanho da imagem de entrada (padrão: 640)"
    )
    parser.add_argument(
        "--calibration-dir",
        default="data/calibration/",
        help="Diretório com imagens de calibração para INT8 (padrão: data/calibration/)"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Executa benchmark de FPS após conversão"
    )
    args = parser.parse_args()

    model_name = os.path.splitext(os.path.basename(args.model))[0]
    if not args.output:
        args.output = os.path.join(
            "models",
            f"{model_name}_openvino_{args.precision.lower()}"
        )

    # Exportação
    ov_dir = export_to_openvino(args.model, args.output, args.precision, args.imgsz)

    # INT8 opcional
    final_dir = ov_dir
    if args.precision == "INT8":
        final_dir = quantize_int8(ov_dir, args.calibration_dir, args.imgsz)

    # Classes do modelo (para metadata)
    try:
        from ultralytics import YOLO
        m = YOLO(args.model)
        class_names = list(m.names.values()) if hasattr(m, "names") else ["pintinho", "galinha"]
    except Exception:
        class_names = ["pintinho", "galinha"]

    # Copia e gera metadata
    copy_and_generate_metadata(
        final_dir, args.output, args.model, args.precision, args.imgsz, class_names
    )

    # Benchmark opcional
    if args.benchmark:
        xml_path = os.path.join(args.output, "model.xml")
        if os.path.exists(xml_path):
            benchmark_model(xml_path, args.imgsz)


if __name__ == "__main__":
    main()
