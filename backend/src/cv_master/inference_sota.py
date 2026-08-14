import logging
import torch

try:
    import supervision as sv
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SUPERVISION_AVAILABLE = True
except ImportError:
    sv = None
    AutoDetectionModel = None
    get_sliced_prediction = None
    SUPERVISION_AVAILABLE = False



class SOTAInferenceEngine:
    def __init__(self, model_path, confidence=0.45, iou_threshold=0.5):
        if not SUPERVISION_AVAILABLE:
            raise RuntimeError("Alguma dependência SOTA (sahi, supervision) está faltando.")
        self.logger = logging.getLogger("cv_master.SOTAInference")
        self.model_path = model_path
        self.confidence = confidence
        self.iou_threshold = iou_threshold

        # Detecção Dinâmica de Aceleração de Hardware
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.logger.info(
            f"Carregando SOTA Model em {model_path} via SAHI (device={self.device})..."
        )

        self.model = AutoDetectionModel.from_pretrained(
            model_type="yolov8",  # YOLOv8/v10/v8-seg são compatíveis com o tipo yolov8 no SAHI
            model_path=model_path,
            confidence_threshold=self.confidence,
            device=self.device,
        )

        # Injeta IOU modificado para NMS se aplicável
        if hasattr(self.model, "engine") and hasattr(self.model.engine, "model"):
            self.model.engine.model.iou = self.iou_threshold

    def process_frame(self, frame, slice_size=640, overlap=0.20):
        """
        Gera predições fatiadas para detectar aves pequenas.
        Retorna obj supervision.Detections
        """
        if frame is None or frame.size == 0:
            return sv.Detections.empty()

        result = get_sliced_prediction(
            frame,
            self.model,
            slice_height=slice_size,
            slice_width=slice_size,
            overlap_height_ratio=overlap,
            overlap_width_ratio=overlap,
            postprocess_class_agnostic=True,
            postprocess_match_metric="IOU",
            verbose=0,
        )

        # Ponte SAHI para Supervision
        detections = sv.Detections.from_sahi(result)
        return detections
