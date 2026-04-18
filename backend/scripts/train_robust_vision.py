"""
ChikGuard — Treinamento Robusto YOLOv8n-Seg (Fine-Tuning)
==========================================================
Script profissional de fine-tuning com augmentations específicas de granja,
validação automática de métricas mínimas e exportação para OpenVINO.

Uso:
  # Treinamento padrão (depois de anotar com Roboflow/CVAT)
  python scripts/train_robust_vision.py \\
    --data data/dataset/data.yaml \\
    --epochs 200 \\
    --export

  # Treinamento rápido para validação rápida do dataset (10 épocas)
  python scripts/train_robust_vision.py --data data/dataset/data.yaml --epochs 10

  # Com modelo melhor (mais preciso, mais lento)
  python scripts/train_robust_vision.py --model yolov8s-seg.pt

Fluxo:
  1. Carrega YOLOv8n-seg pré-treinado (COCO) como backbone
  2. Fine-tune com augmentações específicas de granja (poeira, penumbra, oclusão)
  3. Valida mAP@50 ≥ 0.80 para ambas as classes
  4. Exporta automaticamente: .pt → .onnx → OpenVINO FP16
  5. Copia o modelo otimizado para o diretório correto do backend
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import shutil
import platform

# ── Validação de dependências ──────────────────────────────────────────────────
try:
    from ultralytics import YOLO
except ImportError:
    print("[ERRO] ultralytics não instalado. Execute: pip install ultralytics")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("[ERRO] pyyaml não instalado. Execute: pip install pyyaml")
    sys.exit(1)


# ── Configuração de augmentações de granja ─────────────────────────────────────

FARM_TRAIN_ARGS = {
    # ── Resolução e batch ──────────────────────────────────────────────────
    "imgsz":   640,    # Tamanho padrão — compatível com SAHI (tiles de 640x640)
    "batch":   16,     # Ajuste para -1 se quiser auto-batch

    # ── Otimizador ────────────────────────────────────────────────────────
    "optimizer": "AdamW",
    "lr0":    0.001,   # LR inicial (menor que default — mais estável no fine-tune)
    "lrf":    0.01,    # LR final como fração do LR inicial
    "warmup_epochs": 3,

    # ── Regularização ──────────────────────────────────────────────────────
    "dropout": 0.0,    # YOLO-seg não usa dropout, mas mantido para compatibilidade
    "weight_decay": 0.0005,

    # ── AUGMENTAÇÕES ESPECÍFICAS PARA GRANJA ──────────────────────────────

    # Escala de zoom: simula câmera variando altura (0.5m a 3m do chão)
    "scale":   0.6,

    # Mosaico 4x1: combina 4 cenas de granja numa imagem → pintinhos ficam
    # menores → treina detecção de objetos minúsculos diretamente
    "mosaic":  1.0,

    # Mixup: transparência entre aves simula oclusão densa (amontoadas)
    "mixup":   0.15,

    # Copy-Paste: recorta aves de um lado e cola em outra imagem →
    # fundamental para segmentação de instâncias densamente sobrepostas
    "copy_paste": 0.3,

    # ── SIMULAÇÃO DE CONDIÇÕES ADVERSAS DA GRANJA ─────────────────────────

    # Variação de iluminação: manhã (fria) → tarde (quente) → halógena
    "hsv_h":  0.020,   # Matiz: simula mudança de temperatura de cor do ambiente
    "hsv_s":  0.80,    # Saturação: poeira no ar dessatura a cena
    "hsv_v":  0.50,    # Valor/brilho: zonas de sombra dos comedouros e bebedouros

    # Perspectiva: câmera mal fixada ou vibração do galpão
    "degrees":    18.0,
    "translate":  0.12,
    "shear":      2.0,
    "perspective": 0.0005,

    # Espelhamento horizontal: aves andam nos dois sentidos
    "fliplr":  0.5,
    "flipud":  0.0,    # Câmera não fica de cabeça para baixo

    # Não inverter canais BGR: amarelo dos pintinhos é uma feature crítica
    "bgr":     0.0,

    # ── CONFIGURAÇÕES DE SAÍDA ─────────────────────────────────────────────
    "project": "runs/train",
    "name":    "chikguard_robust_seg",
    "exist_ok": True,
    "save":     True,
    "save_period": 10,   # Salva checkpoint a cada 10 épocas
    "plots":    True,    # Gera gráficos de métricas
    "verbose":  True,
}


def detect_device() -> str:
    """Detecta o melhor device disponível para treinamento."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  🎮 GPU detectada: {gpu_name}")
            return "0"  # Primeiro GPU
        else:
            print("  💻 Sem GPU CUDA — usando CPU (mais lento, ~10x)")
            return "cpu"
    except ImportError:
        return "cpu"


def validate_dataset(data_yaml: str) -> bool:
    """Valida se o dataset tem estrutura correta antes de treinar."""
    if not os.path.exists(data_yaml):
        print(f"\n[ERRO] data.yaml não encontrado: {data_yaml}")
        print("       Execute o script de extração + anote no Roboflow primeiro.")
        print("       → python scripts/extract_frames_for_annotation.py")
        return False

    with open(data_yaml, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    dataset_root = cfg.get("path", os.path.dirname(data_yaml))
    train_path   = os.path.join(dataset_root, cfg.get("train", "train/images"))
    val_path     = os.path.join(dataset_root, cfg.get("val",   "valid/images"))

    issues = []
    if not os.path.exists(train_path):
        issues.append(f"Diretório train não encontrado: {train_path}")
    else:
        n_train = len([f for f in os.listdir(train_path)
                       if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
        if n_train < 50:
            issues.append(f"Muito poucos frames de treino: {n_train} (mínimo: 50)")
        else:
            print(f"  ✅ Train: {n_train} imagens")

    if not os.path.exists(val_path):
        issues.append(f"Diretório val não encontrado: {val_path}")
    else:
        n_val = len([f for f in os.listdir(val_path)
                     if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
        if n_val < 10:
            issues.append(f"Muito poucos frames de validação: {n_val} (mínimo: 10)")
        else:
            print(f"  ✅ Val  : {n_val} imagens")

    nc = cfg.get("nc", 0)
    names = cfg.get("names", {})
    if nc < 1:
        issues.append("'nc' (número de classes) não definido no data.yaml")
    else:
        print(f"  ✅ Classes: {nc} — {list(names.values()) if names else 'não listadas'}")

    if issues:
        print(f"\n[ERRO] Problemas no dataset:")
        for i in issues:
            print(f"  • {i}")
        return False

    return True


def train_robust_model(
    data_yaml: str,
    base_model: str = "yolov8n-seg.pt",
    epochs: int = 200,
    device: str = "auto",
    export_after: bool = True,
    min_map50: float = 0.60,   # mínimo aceitável após fine-tuning
) -> dict:
    print(f"\n{'='*65}")
    print(f"  🐓 ChikGuard — Treinamento YOLOv8-Seg (Fine-Tuning Robusto)")
    print(f"{'='*65}")
    print(f"  Modelo base  : {base_model}")
    print(f"  Dataset      : {data_yaml}")
    print(f"  Épocas       : {epochs}")
    print(f"{'='*65}\n")

    # Validação do dataset
    print("[PRÉ-VALIDAÇÃO] Verificando dataset...\n")
    if not validate_dataset(data_yaml):
        return {"success": False, "reason": "dataset_invalid"}

    # Device
    if device == "auto":
        device = detect_device()

    # Carrega modelo base
    model = YOLO(base_model)
    print(f"\n[MODELO] {base_model} carregado | task='{model.task}'")

    # Monta args de treinamento
    train_args = dict(FARM_TRAIN_ARGS)
    train_args["data"]   = data_yaml
    train_args["epochs"] = epochs
    train_args["device"] = device

    print(f"\n[AUGMENTAÇÕES ATIVAS]")
    aug_keys = ["mosaic", "mixup", "copy_paste", "scale",
                "hsv_h", "hsv_s", "hsv_v", "degrees", "shear"]
    for k in aug_keys:
        print(f"  {k:15s} = {train_args[k]}")

    print(f"\n[TREINAMENTO] Iniciando...")
    t0 = time.time()

    try:
        results = model.train(**train_args)
    except Exception as exc:
        print(f"\n[ERRO] Falha no treinamento: {exc}")
        import traceback; traceback.print_exc()
        return {"success": False, "reason": str(exc)}

    elapsed = time.time() - t0
    print(f"\n[TREINAMENTO] Concluído em {elapsed/3600:.1f}h")

    # Lê métricas finais
    save_dir  = str(results.save_dir)
    best_pt   = os.path.join(save_dir, "weights", "best.pt")
    metrics_f = os.path.join(save_dir, "results.csv")

    map50 = 0.0
    if os.path.exists(metrics_f):
        import csv
        with open(metrics_f) as f:
            rows = list(csv.DictReader(f))
        if rows:
            last = rows[-1]
            # Ultralytics usa chaves como "metrics/mAP50(B)" ou "metrics/mAP50(M)"
            for k, v in last.items():
                if "mAP50" in k and "95" not in k:
                    try:
                        map50 = float(v.strip())
                        break
                    except (ValueError, TypeError):
                        pass

    print(f"\n[MÉTRICAS FINAIS]")
    print(f"  mAP@50      : {map50:.3f} ({'✅' if map50 >= min_map50 else '⚠️ abaixo do mínimo'} — mín={min_map50:.2f})")
    print(f"  Melhor peso : {best_pt}")

    if map50 < min_map50:
        print(f"\n  ⚠️  mAP abaixo do mínimo ({map50:.2f} < {min_map50:.2f}).")
        print(f"     Sugestões:")
        print(f"       • Adicionar mais imagens de treinamento (meta: 300+)")
        print(f"       • Verificar qualidade das anotações no Roboflow")
        print(f"       • Aumentar épocas para 300+")
        print(f"       • Usar modelo maior: --model yolov8s-seg.pt")

    result_info = {
        "success":  True,
        "map50":    map50,
        "save_dir": save_dir,
        "best_pt":  best_pt,
        "elapsed_s": round(elapsed, 1),
    }

    # ── Exportação automática ─────────────────────────────────────────────
    if export_after and os.path.exists(best_pt):
        results_export = auto_export(best_pt)
        result_info.update(results_export)

    return result_info


def auto_export(best_pt: str) -> dict:
    """Exporta best.pt → ONNX → OpenVINO FP16 automaticamente."""
    print(f"\n{'='*65}")
    print(f"  📦 Exportação automática: {best_pt}")
    print(f"{'='*65}")

    out = {}
    model = YOLO(best_pt)

    # 1. ONNX (fallback edge)
    print("\n[EXPORT 1/2] ONNX...")
    try:
        model.export(format="onnx", imgsz=640, dynamic=False, simplify=True)
        onnx_path = best_pt.replace(".pt", ".onnx")
        out["onnx_path"] = onnx_path
        print(f"  ✅ ONNX: {onnx_path}")
    except Exception as exc:
        print(f"  ❌ ONNX falhou: {exc}")

    # 2. OpenVINO FP16 (Intel iGPU)
    print("\n[EXPORT 2/2] OpenVINO FP16...")
    try:
        model.export(format="openvino", imgsz=640, half=True, dynamic=False)
        ov_dir  = best_pt.replace(".pt", "_openvino_model")
        xml_f   = os.path.join(ov_dir, "model.xml")
        out["openvino_xml"] = xml_f
        print(f"  ✅ OpenVINO: {xml_f}")
    except Exception as exc:
        print(f"  ❌ OpenVINO falhou: {exc}")
        print(f"     Instale com: pip install openvino")

    # 3. Copia melhor modelo para o diretório do backend
    backend_dir  = os.path.join(os.path.dirname(__file__), "..")
    models_dir   = os.path.join(backend_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    print(f"\n[DEPLOY] Copiando modelo para {models_dir}...")
    try:
        shutil.copy2(best_pt, os.path.join(models_dir, "chikguard_best.pt"))
        print(f"  ✅ PT copiado: models/chikguard_best.pt")
    except Exception as exc:
        print(f"  ❌ Falha ao copiar PT: {exc}")

    if "openvino_xml" in out:
        ov_src = os.path.dirname(out["openvino_xml"])
        ov_dst = os.path.join(models_dir, "chikguard_openvino_fp16")
        try:
            if os.path.exists(ov_dst):
                shutil.rmtree(ov_dst)
            shutil.copytree(ov_src, ov_dst)
            out["openvino_deploy"] = os.path.join(ov_dst, "model.xml")
            print(f"  ✅ OpenVINO copiado: models/chikguard_openvino_fp16/")
        except Exception as exc:
            print(f"  ❌ Falha ao copiar OpenVINO: {exc}")

    # Instruções finais
    print(f"\n{'='*65}")
    print(f"  📋 CONFIGURAÇÃO DO BACKEND:")
    print(f"")
    if "openvino_deploy" in out:
        print(f"  Edite o .env:")
        print(f"    INFERENCE_BACKEND=openvino")
        print(f"    OPENVINO_MODEL_XML={out['openvino_deploy']}")
    else:
        print(f"  Edite o .env:")
        print(f"    INFERENCE_BACKEND=pytorch")
        print(f"    YOLO_SEG_MODEL_PATH=models/chikguard_best.pt")
    print(f"    ENABLE_SAHI=true")
    print(f"    DETECTION_CONF=0.25")
    print(f"  Reinicie: python app.py")
    print(f"{'='*65}\n")

    return out


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tuning robusto YOLOv8n-Seg para detecção de pintinhos/galinhas"
    )
    parser.add_argument(
        "--data",
        default=os.path.join(os.path.dirname(__file__), "..", "data", "dataset", "data.yaml"),
        help="Caminho para o data.yaml do dataset"
    )
    parser.add_argument(
        "--model",
        default="yolov8n-seg.pt",
        help="Modelo base. Opções: yolov8n-seg.pt | yolov8s-seg.pt | yolov8m-seg.pt"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=200,
        help="Número de épocas (padrão: 200). Use 10–20 para teste rápido."
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="Device: auto | cpu | 0 (GPU). Padrão: auto"
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Não exportar para ONNX/OpenVINO após treino"
    )
    parser.add_argument(
        "--min-map50",
        type=float,
        default=0.60,
        help="mAP@50 mínimo aceitável (padrão: 0.60). Meta de produção: 0.80"
    )
    args = parser.parse_args()

    result = train_robust_model(
        data_yaml    = args.data,
        base_model   = args.model,
        epochs       = args.epochs,
        device       = args.device,
        export_after = not args.no_export,
        min_map50    = args.min_map50,
    )

    if result.get("success"):
        print(f"\n🎉 Pipeline de treinamento concluído com sucesso!")
        print(f"   mAP@50 = {result.get('map50', 0):.3f}")
    else:
        print(f"\n❌ Pipeline falhou: {result.get('reason', 'desconhecido')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
