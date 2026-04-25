import logging
import cv2
import numpy as np

try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    import supervision as sv
except ImportError:
    raise RuntimeError("Alguma dependência SOTA (sahi, supervision) está faltando.")

class SOTAInferenceEngine:
    def __init__(self, model_path, confidence=0.45, iou_threshold=0.5):
        """
        Engine SOTA utilizando ONNX Runtime (preferencialmente TensorRT)
        e SAHI para detecção otimizada de alvos em oclusão severa.
        """
        self.logger = logging.getLogger("cv_master.SOTAInference")
        self.model_path = model_path
        self.confidence = confidence
        self.iou_threshold = iou_threshold
        
        self.logger.info(f"Carregando SOTA Model em {model_path} via ONNX/TensorRT...")
        
        # O Sahi detecta a extensão (.onnx) e tenta injetar os providers de hardware.
        # Caso seja PT, recairá para PyTorch na lib ultralytics padrão.
        self.model = AutoDetectionModel.from_pretrained(
            model_type="yolov8", # Compatível com YOLOv8/v10 padrão SAHI
            model_path=model_path,
            confidence_threshold=self.confidence,
            device="cuda:0"
        )
        # Injeta IOU modificado para desempate de NMS
        if hasattr(self.model, "engine") and hasattr(self.model.engine, "model"):
            self.model.engine.model.iou = self.iou_threshold

    def process_frame(self, frame, slice_size=640, overlap=0.20):
        """
        Gera predições fatiadas para detectar aves pequenas.
        Retorna obj supervision.Detections
        """
        result = get_sliced_prediction(
            frame,
            self.model,
            slice_height=slice_size,
            slice_width=slice_size,
            overlap_height_ratio=overlap,
            overlap_width_ratio=overlap,
            postprocess_class_agnostic=True,
            postprocess_match_metric="IOU"
        )
        
        # Ponte SAHI para Supervision
        detections = sv.Detections.from_sahi(result)
        return detections
