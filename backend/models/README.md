# Models — Download Instructions

This directory is where ChikGuard expects its ML model weights at runtime.

> [!IMPORTANT]
> Model files (`.pt`, `.onnx`) are **not included in this repository** because of their size.
> You must download them manually before running the backend.

---

## Required Models

| File | Purpose | Size | Source |
|---|---|---|---|
| `yolov8n.pt` | Bird detection (training/fine-tune) | ~6.5 MB | [Ultralytics](https://github.com/ultralytics/assets/releases) |
| `yolov8n-seg.pt` | Bird segmentation (training/fine-tune) | ~6.8 MB | [Ultralytics](https://github.com/ultralytics/assets/releases) |
| `yolov8n-seg.onnx` | Bird segmentation (inference, optimized) | ~6.7 MB | Export from `.pt` (see below) |

---

## How to Download

### Option 1 — Ultralytics CLI (recommended)

```bash
pip install ultralytics
yolo export model=yolov8n.pt format=onnx   # exports yolov8n.onnx
yolo export model=yolov8n-seg.pt format=onnx
```

### Option 2 — Direct download

```bash
# YOLOv8n (detection)
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt -P backend/models/

# YOLOv8n-seg (segmentation)
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-seg.pt -P backend/models/
```

### Option 3 — Export ONNX from .pt

```bash
cd backend
python scripts/model_export_pipeline.sh
```

---

## Directory Structure (after download)

```
backend/models/
├── README.md         ← this file
├── yolov8n.pt
├── yolov8n-seg.pt
└── yolov8n-seg.onnx
```

---

## Custom / Fine-tuned Models

If you trained a custom model on your own farm data, place it here and update the model path in `backend/.env`:

```env
YOLO_MODEL_PATH=models/my_custom_model.onnx
```
