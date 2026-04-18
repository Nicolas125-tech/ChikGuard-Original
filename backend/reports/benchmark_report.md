# ChikGuard AI — Relatório de Benchmark Comparativo
## Pipeline de Visão Computacional: Antes vs. Depois

> 📅 Gerado em: 2026-04-18 | Hardware: Intel Mini PC Linux

---

## 🔴 Estado Anterior (Sistema Inviável)

| Métrica | Valor | Avaliação |
|---|---|---|
| **Aves detectadas** (frame de controle) | **2 de ~30+** | ❌ Crítico |
| **Confiança média** | **~36%** | ❌ Inaceitável |
| **FPS da câmera** | 10 FPS | — |
| **FPS de inferência** | **1 FPS** | ❌ Crítico |
| **Latência por frame** | ~297 ms | ❌ |
| **Modelo** | YOLOv8n — COCO genérico | Nunca viu pintinho |
| **Backend** | PyTorch CPU | Sem aceleração |
| **Modo SAHI** | Desabilitado | — |
| **Separação individual** | Bounding boxes sobrepostas | Não distingue indivíduos |

### Causas-raiz identificadas:

1. **Modelo sem fine-tune**: O YOLOv8n-COCO nunca foi treinado em pintinhos/galinhas de granja. Detecta "bird" da classe genérica, com baixíssima confiança nesta cena.

2. **Inferência síncrona no loop principal**: `detector.detect()` bloqueava a captura da câmera — a cada frame inferido, 9+ frames da câmera eram descartados.

3. **Redimensionamento destrutivo**: Frame 1080p comprimido para 640×360px. Um pintinho de 30×30px real vira ≈3×3px após resize — sub-resolução para qualquer rede neural.

4. **`ENABLE_SAHI=False` por padrão**: O SAHI estava implementado mas desabilitado.

---

## 🟢 Estado Após Reescrita (Estimativas / Projeções)

> Os valores abaixo são projeções baseadas na literatura de SAHI + OpenVINO + YOLOv8n.
> **Medições reais** devem ser executadas após fine-tuning do modelo.

### Com modelo COCO genérico + SAHI ativo (melhoria imediata)

| Métrica | Antes | Depois SAHI | Ganho |
|---|---|---|---|
| Aves detectadas (frame controle) | 2 | **12–20** | 6–10× |
| Confiança média | 36% | ~45–55% | +25% |
| FPS câmera | 10 | 10–30 | Desacoplado |
| FPS inferência (CPU) | 1 | **4–7** | ~5× |
| Latência SAHI (8 tiles, 4 workers) | 297ms | **120–180ms** | ~2× |
| Backend | PyTorch | PyTorch (SAHI) | — |

### Com fine-tune do modelo + OpenVINO FP16 (produção)

| Métrica | Antes | Meta Produção | Ganho |
|---|---|---|---|
| Aves detectadas (frame controle) | 2 | **25–35+** | 15–17× |
| Confiança média | 36% | **≥ 80%** | +122% |
| FPS câmera | 10 | 10–30 | Desacoplado ✅ |
| FPS inferência | 1 | **≥ 20 FPS** | 20× |
| Latência por frame | 297ms | **< 50ms** | 6× |
| Backend | PyTorch CPU | OpenVINO FP16 (iGPU) | — |
| Separação individual | Boxes sobrepostas | **Máscaras de instância** | ✅ |
| Rastreamento cross-frame | IoU simples | **ByteTrack estável** | ✅ |

### Por que OpenVINO FP16 é 4–6× mais rápido que PyTorch na Intel?

| Componente | PyTorch CPU | OpenVINO FP16 + iGPU |
|---|---|---|
| Quantização de pesos | FP32 (32-bit) | FP16 (16-bit) — metade da memória |
| Instrução de CPU | AVX2 (genérico) | Intel DL Boost + AVX-512 VNNI |
| GPU integrada | Não utiliza | Execução parcial na iGPU Intel |
| Overhead do framework | Alto (Python) | Compilação estática (C++) |

---

## 📐 Arquitetura SAHI para 1080p

```
Frame 1920×1080px
       │
   ┌───┴───────────────────────────────────────────┐
   │              SAHITileEngine                    │
   │   stride_x = 640 × 0.80 = 512px               │
   │   stride_y = 640 × 0.80 = 512px               │
   │                                                │
   │   Tile layout (estimado para 1920×1080):       │
   │   ┌──────┬──────┬──────┬──────┐               │
   │   │ T1   │ T2   │ T3   │ T4   │               │
   │   │640px │ ←512 │ ←512 │ bord │               │
   │   ├──────┼──────┼──────┼──────┤               │
   │   │ T5   │ T6   │ T7   │ T8   │               │
   │   │  ↑512│      │      │ bord │               │
   │   └──────┴──────┴──────┴──────┘               │
   │                                                │
   │   Total: ~8 tiles por frame                    │
   │   Sobreposição: 20% (128px) em cada borda      │
   └───┬───────────────────────────────────────────┘
       │
   ThreadPoolExecutor (4 workers)
   ┌───┴──────────────────────────┐
   │ Worker 1: T1, T5            │
   │ Worker 2: T2, T6            │
   │ Worker 3: T3, T7            │
   │ Worker 4: T4, T8            │
   └───┬──────────────────────────┘
       │
   NMS Global (IoU 0.45)
   Elimina duplicatas nas bordas sobrepostas
       │
   Detecções finais no espaço do frame completo
```

### Por que um pintinho de 30×30px é detectado com SAHI?

| Cenário | Sem SAHI | Com SAHI |
|---|---|---|
| Frame 1080p → input rede | 30px → **3px** após resize 640px | Tile 640×640 cobre 640px do frame original |
| Pixels visíveis a rede | **3×3 = 9 pixels** — sub-threshold | **~30×30 = 900 pixels** — detectável |
| Confiança resultante | ~15-25% → descartada | **55-80%** → aceita |

---

## 🛣️ Roadmap de Produção

```
Fase 1 (IMEDIATO — hoje):
  ✅ SAHITileEngine nativo ativo (ENABLE_SAHI=true)
  ✅ Backend adaptativo (OpenVINO → ONNX → PyTorch)
  ✅ HUD com métricas SAHI + backend name
  → Resultado esperado: 4–7 FPS inferência, 12–20 aves detectadas

Fase 2 (1–2 semanas — Dataset):
  □ Extrair 200 frames do video_granja.mp4
    python scripts/extract_frames_for_annotation.py
  □ Anotar com Roboflow (polígonos de segmentação)
  □ Fine-tuning:
    python scripts/train_robust_vision.py --data data/dataset/data.yaml

Fase 3 (No Mini PC Linux — Deploy de produção):
  □ Instalar OpenVINO: pip install openvino
  □ Converter modelo: python scripts/convert_to_openvino.py --model models/chikguard_best.pt
  □ Configurar .env: INFERENCE_BACKEND=openvino
  → Resultado esperado: ≥20 FPS, ≥80% confiança, 25–35 aves detectadas
```

---

## 🔧 Comandos de Referência (Linux — Mini PC)

```bash
# 1. Instalar dependências de edge
pip install openvino ultralytics sahi

# 2. Extrair frames para anotação
cd backend
python scripts/extract_frames_for_annotation.py \
  --video video_granja.mp4 \
  --output data/annotation_frames/ \
  --count 200

# 3. Após anotação no Roboflow → treinamento (requer dataset em data/dataset/)
python scripts/train_robust_vision.py \
  --data data/dataset/data.yaml \
  --epochs 200

# 4. Converter para OpenVINO FP16
python scripts/convert_to_openvino.py \
  --model models/chikguard_best.pt \
  --precision FP16 \
  --benchmark

# 5. Configurar .env e reiniciar
# INFERENCE_BACKEND=openvino
# OPENVINO_MODEL_XML=models/chikguard_openvino_fp16/model.xml
# ENABLE_SAHI=true
# DETECTION_CONF=0.25
python app.py
```
