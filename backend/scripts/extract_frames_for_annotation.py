"""
ChikGuard — Extração de Frames para Anotação (Dataset Bootstrap)
=================================================================
Extrai frames diversos e de alta qualidade do vídeo da câmera de granja
para serem anotados no Roboflow ou CVAT como passo zero do fine-tuning.

Estratégia de extração inteligente:
  1. Extrai 1 frame a cada N segundos (configurável)
  2. Aplica filtro de qualidade (descarta frames borrados/escuros)
  3. Maximiza diversidade via hash perceptual (evita frames quase idênticos)
  4. Salva em resolução original (não redimensiona — preserva detalhe dos pintinhos)

Uso:
  python scripts/extract_frames_for_annotation.py \\
    --video video_granja.mp4 \\
    --output data/annotation_frames/ \\
    --count 200 \\
    --min-quality 0.4

Meta de anotação sugerida:
  • 150–300 imagens com polígonos de segmentação de instância
  • Use Roboflow (https://roboflow.com) — gratuito até 1000 imagens
  • Exporte no formato "YOLOv8 Segmentation" (.yaml + train/val/test/)
  • Concentre em cenas variadas: pintinhos dispersos, amontoados, penumbra
"""

import argparse
import os
import sys
import json
import hashlib
from pathlib import Path

import cv2
import numpy as np


# ── Utilitários de qualidade ──────────────────────────────────────────────────

def _blur_score(frame: np.ndarray) -> float:
    """Retorna a variância do Laplaciano (0 = muito borrado, >100 = nítido)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _brightness_score(frame: np.ndarray) -> float:
    """Retorna o brilho médio do frame (0 = preto, 1 = branco)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray)) / 255.0


def _perceptual_hash(frame: np.ndarray, size: int = 16) -> str:
    """
    Hash perceptual simples (Average Hash 16x16).
    Frames muito similares terão hashes próximos — usamos distância de Hamming
    para verificar diversidade.
    """
    small = cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA)
    gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    mean  = np.mean(gray)
    bits  = (gray > mean).flatten()
    return "".join("1" if b else "0" for b in bits)


def _hamming_distance(h1: str, h2: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(h1, h2))


def _quality_label(blur: float, brightness: float) -> str:
    """Retorna label legível de qualidade para o log."""
    issues = []
    if blur < 80:
        issues.append("borrado")
    if brightness < 0.15:
        issues.append("escuro")
    if brightness > 0.90:
        issues.append("superexposto")
    return " + ".join(issues) if issues else "ok"


# ── Seleção inteligente de frames ────────────────────────────────────────────

def extract_frames(
    video_path: str,
    output_dir: str,
    target_count: int = 200,
    min_blur_score: float = 80.0,
    min_brightness: float = 0.12,
    max_brightness: float = 0.92,
    min_hamming_dist: int = 15,      # Diversidade mínima entre frames selecionados
    verbose: bool = True,
) -> dict:
    """
    Extrai frames representativos do vídeo de granja.

    Returns:
        dict com estatísticas da extração
    """
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERRO] Não foi possível abrir o vídeo: {video_path}")
        sys.exit(1)

    total_frames  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_video     = cap.get(cv2.CAP_PROP_FPS) or 10.0
    duration_sec  = total_frames / fps_video
    width         = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height        = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"\n{'='*60}")
    print(f"  ChikGuard — Extração de Frames para Anotação")
    print(f"{'='*60}")
    print(f"  Vídeo    : {video_path}")
    print(f"  Duração  : {duration_sec:.1f}s  ({total_frames} frames @ {fps_video:.1f} FPS)")
    print(f"  Resolução: {width}×{height}px")
    print(f"  Meta     : {target_count} frames diversificados")
    print(f"{'='*60}\n")

    # Distribui timestamps uniformemente pelo vídeo para cobertura máxima
    # Adiciona margem de 5% no início e no fim
    margin = int(total_frames * 0.05)
    candidate_positions = np.linspace(
        margin,
        total_frames - margin,
        num=min(target_count * 8, total_frames),  # 8x candidatos
        dtype=int,
    )

    saved = 0
    skipped_blur    = 0
    skipped_bright  = 0
    skipped_similar = 0
    hashes_saved    = []
    metadata_rows   = []

    for pos in candidate_positions:
        if saved >= target_count:
            break

        cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        # Verificação de qualidade
        blur   = _blur_score(frame)
        bright = _brightness_score(frame)

        if blur < min_blur_score:
            skipped_blur += 1
            continue
        if not (min_brightness <= bright <= max_brightness):
            skipped_bright += 1
            continue

        # Verificação de diversidade (hash perceptual)
        ph = _perceptual_hash(frame)
        too_similar = any(
            _hamming_distance(ph, h) < min_hamming_dist for h in hashes_saved
        )
        if too_similar:
            skipped_similar += 1
            continue

        # Salva o frame
        ts_sec    = pos / fps_video
        filename  = f"frame_{saved:04d}_t{ts_sec:.1f}s.jpg"
        out_path  = os.path.join(output_dir, filename)
        cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        hashes_saved.append(ph)
        metadata_rows.append({
            "index":        saved,
            "filename":     filename,
            "frame_pos":    int(pos),
            "timestamp_s":  round(ts_sec, 2),
            "blur_score":   round(blur, 1),
            "brightness":   round(bright, 3),
        })
        saved += 1

        if verbose and saved % 20 == 0:
            print(f"  [{saved:3d}/{target_count}] frame {pos:5d} | "
                  f"blur={blur:.0f} bright={bright:.2f} → salvo: {filename}")

    cap.release()

    # Salva metadata.json para rastreabilidade
    meta_path = os.path.join(output_dir, "extraction_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "source_video":    video_path,
            "total_extracted": saved,
            "skipped_blur":    skipped_blur,
            "skipped_bright":  skipped_bright,
            "skipped_similar": skipped_similar,
            "frames":          metadata_rows,
        }, f, ensure_ascii=False, indent=2)

    # Relatório final
    stats = {
        "saved":            saved,
        "skipped_blur":     skipped_blur,
        "skipped_bright":   skipped_bright,
        "skipped_similar":  skipped_similar,
        "output_dir":       output_dir,
    }

    print(f"\n{'='*60}")
    print(f"  ✅ Extração concluída!")
    print(f"  Frames salvos    : {saved}")
    print(f"  Descartados      : {skipped_blur} (borrado) + "
          f"{skipped_bright} (brilho) + {skipped_similar} (similares)")
    print(f"  Diretório        : {output_dir}")
    print(f"  Metadata         : {meta_path}")
    print(f"{'='*60}")
    print(f"""
  📋 PRÓXIMOS PASSOS (Anotação):

  1. Abra https://universe.roboflow.com → "Create Project"
     → Object Detection → Segmentation (Instance)

  2. Crie 2 classes:
     • "pintinho"  (chick)
     • "galinha"   (hen)

  3. Upload dos {saved} frames de: {output_dir}

  4. Anote manualmente com a ferramenta "Smart Polygon":
     → Clique na ave → Roboflow sugere o polígono automaticamente
     → Meta: 150–200 imagens anotadas é suficiente para fine-tuning

  5. Exporte em formato "YOLOv8 Segmentation"
     → Download ZIP → extraia em: backend/data/dataset/

  6. Execute o treinamento:
     python scripts/train_robust_vision.py

  ⏱ Estimativa: 2–4 horas de anotação para 200 imagens
""")
    return stats


def generate_data_yaml(output_dir: str, dataset_dir: str):
    """Gera o data.yaml base para o treinamento YOLOv8-Seg."""
    yaml_content = f"""# ChikGuard — Dataset de Segmentação de Instância
# Gerado por extract_frames_for_annotation.py
# Edite os caminhos após exportar do Roboflow/CVAT

path: {os.path.abspath(dataset_dir)}  # raiz do dataset

train: train/images   # imagens de treino
val:   valid/images   # imagens de validação
test:  test/images    # imagens de teste (opcional)

nc: 2                 # número de classes
names:
  0: pintinho         # chick (1–14 dias, amarelo, pequeno)
  1: galinha          # hen (adulta, branca/marrom, grande)

# Dicas de anotação:
# - Anote com polígonos de segmentação de instância, não bounding boxes
# - Um polígono por ave, mesmo amontoadas
# - Inclua aves parcialmente visíveis nas bordas
# - Anote TODAS as aves na imagem (não pular as pequenas ao fundo)
"""
    yaml_path = os.path.join(dataset_dir, "data.yaml")
    os.makedirs(dataset_dir, exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"\n  📄 data.yaml gerado em: {yaml_path}")
    return yaml_path


def main():
    parser = argparse.ArgumentParser(
        description="Extrai frames diversificados de vídeo de granja para anotação"
    )
    parser.add_argument(
        "--video",
        default="video_granja.mp4",
        help="Caminho para o vídeo de granja (padrão: video_granja.mp4)"
    )
    parser.add_argument(
        "--output",
        default="data/annotation_frames/",
        help="Diretório de saída dos frames (padrão: data/annotation_frames/)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=200,
        help="Número de frames a extrair (padrão: 200)"
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=80.0,
        help="Score mínimo de nitidez Laplaciana (padrão: 80)"
    )
    parser.add_argument(
        "--min-hamming",
        type=int,
        default=15,
        help="Distância mínima de Hamming entre frames (diversidade, padrão: 15)"
    )
    parser.add_argument(
        "--gen-yaml",
        action="store_true",
        help="Gera o data.yaml base para treinamento no diretório data/dataset/"
    )
    args = parser.parse_args()

    # Encontra o vídeo relativo ao diretório do backend
    video_path = args.video
    if not os.path.exists(video_path):
        # Tenta encontrar relativo ao script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path   = os.path.join(script_dir, "..", args.video)
        if os.path.exists(alt_path):
            video_path = os.path.normpath(alt_path)
        else:
            print(f"[ERRO] Vídeo não encontrado: {args.video}")
            print(f"       Passe o caminho completo com --video /caminho/para/video.mp4")
            sys.exit(1)

    extract_frames(
        video_path   = video_path,
        output_dir   = args.output,
        target_count = args.count,
        min_blur_score = args.min_quality,
        min_hamming_dist = args.min_hamming,
    )

    if args.gen_yaml:
        generate_data_yaml(args.output, "data/dataset/")


if __name__ == "__main__":
    main()
