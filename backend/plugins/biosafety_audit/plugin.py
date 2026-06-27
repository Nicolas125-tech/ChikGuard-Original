import logging
import time
from typing import Any, Dict, List, Optional
import numpy as np

from src.plugins.base import PluginBase, PluginInfo

logger = logging.getLogger(__name__)


def _log_event(
    event_type: str,
    level: str = "info",
    message: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    camera_id: str = "stream",
    frame: Optional[np.ndarray] = None,
):
    """
    Helper para registrar eventos no sistema central do ChikGuard.
    Tenta delegar para o app_flask_legacy._log_event dinamicamente.
    """
    try:
        from app_flask_legacy import _log_event as legacy_log
        legacy_log(
            event_type=event_type,
            level=level,
            message=message,
            metadata=metadata,
            camera_id=camera_id,
            frame=frame,
        )
    except Exception as exc:
        logger.debug("Falha ao propagar evento para o core (fora do contexto web): %s", exc)


class BiosafetyAuditPlugin(PluginBase):
    info = PluginInfo(
        name="biosafety_audit",
        version="1.0.0",
        description="Auditoria de Biossegurança de Fronteira (EPIs e Veículos)",
    )

    def __init__(self):
        self.model = None
        self.model_path = "yolov8n-epi.engine"
        self.required_epis = ["helmet", "vest", "boots"]
        
        # Mapeamento padrão de classes (pode ser sobrescrito ao carregar o modelo)
        self.class_to_label = {
            0: "person",
            1: "helmet",
            2: "vest",
            3: "boots",
            4: "mask",
            5: "gloves",
            6: "vehicle",
        }
        
        # Mapeamento reverso para facilitar a indexação
        self.label_to_class = {v: k for k, v in self.class_to_label.items()}

    def on_startup(self, context: Dict[str, Any]) -> None:
        """
        Carrega o modelo YOLOv8 customizado para EPIs.
        """
        from ultralytics import YOLO

        settings = context.get("settings", {})
        if hasattr(settings, "get"):
            self.model_path = settings.get("BIOSAFETY_MODEL_PATH", "yolov8n-epi.engine")
            self.required_epis = settings.get("BIOSAFETY_REQUIRED_EPIS", ["helmet", "vest", "boots"])
        else:
            self.model_path = getattr(settings, "biosafety_model_path", None) or getattr(settings, "BIOSAFETY_MODEL_PATH", "yolov8n-epi.engine")
            self.required_epis = getattr(settings, "biosafety_required_epis", None) or getattr(settings, "BIOSAFETY_REQUIRED_EPIS", ["helmet", "vest", "boots"])


        # Carrega o modelo com fallback
        try:
            self.model = YOLO(self.model_path)
            logger.info("Modelo de biossegurança carregado com sucesso: %s", self.model_path)
            
            # Atualiza o mapeamento de classes dinamicamente se o modelo tiver nomes definidos
            if hasattr(self.model, "names") and self.model.names:
                self._build_class_mapping(self.model.names)
        except Exception as exc:
            logger.warning(
                "Falha ao carregar o modelo em '%s' (%s). Usando fallback local 'yolov8n.pt'",
                self.model_path,
                exc,
            )
            try:
                self.model = YOLO("yolov8n.pt")
                if hasattr(self.model, "names") and self.model.names:
                    self._build_class_mapping(self.model.names)
            except Exception as final_exc:
                logger.error("Erro crítico: impossível inicializar modelo YOLO: %s", final_exc)

    def _build_class_mapping(self, model_names: Dict[int, str]) -> None:
        """
        Mapeia de forma inteligente as classes do modelo carregado para os rótulos conhecidos.
        """
        new_mapping = {}
        for idx, name in model_names.items():
            name_lower = name.lower()
            if "person" in name_lower:
                new_mapping[idx] = "person"
            elif "helmet" in name_lower or "hard-hat" in name_lower or "capacete" in name_lower:
                new_mapping[idx] = "helmet"
            elif "vest" in name_lower or "colete" in name_lower:
                new_mapping[idx] = "vest"
            elif "boot" in name_lower or "bota" in name_lower or "shoe" in name_lower:
                new_mapping[idx] = "boots"
            elif "mask" in name_lower or "mascara" in name_lower:
                new_mapping[idx] = "mask"
            elif "glove" in name_lower or "luva" in name_lower:
                new_mapping[idx] = "gloves"
            elif any(v in name_lower for v in ["car", "truck", "bus", "vehicle", "veiculo"]):
                new_mapping[idx] = "vehicle"
                
        if "person" in new_mapping.values():
            self.class_to_label = new_mapping
            self.label_to_class = {v: k for k, v in self.class_to_label.items()}
            logger.info("Mapeamento de classes atualizado dinamicamente: %s", self.class_to_label)

    def _check_overlap(self, box_epi: np.ndarray, box_person: np.ndarray, threshold: float = 0.5) -> bool:
        """
        Verifica se a caixa do EPI está contida ou se sobrepõe significativamente à caixa da pessoa.
        """
        ex1, ey1, ex2, ey2 = box_epi
        px1, py1, px2, py2 = box_person

        # Coordenadas da interseção
        ix1 = max(ex1, px1)
        iy1 = max(ey1, py1)
        ix2 = min(ex2, px2)
        iy2 = min(ey2, py2)

        if ix1 >= ix2 or iy1 >= iy2:
            return False

        intersection_area = (ix2 - ix1) * (iy2 - iy1)
        epi_area = (ex2 - ex1) * (ey2 - ey1)

        if epi_area <= 0:
            return False

        # Se pelo menos 50% (ou threshold) da área do EPI está contida na área da pessoa
        return (intersection_area / epi_area) >= threshold

    def process_frame(self, frame: np.ndarray, camera_zone: str) -> Optional[List[Dict[str, Any]]]:
        """
        Executa a análise do frame apenas se a zona da câmera for de fronteira (ENTRANCE / SANITARY_BARRIER).
        Busca violações de conformidade de EPI e rastreia entrada de veículos.
        """
        if camera_zone not in {"ENTRANCE", "SANITARY_BARRIER"}:
            return None

        if self.model is None:
            # Carrega o YOLO sob demanda se não estiver inicializado (ex: testes sem on_startup)
            from ultralytics import YOLO
            try:
                self.model = YOLO(self.model_path)
            except Exception:
                self.model = YOLO("yolov8n.pt")

        # Roda inferência de detecção pura (sem ByteTrack para as aves!)
        results = self.model.predict(frame, verbose=False)
        if not results:
            return []

        result = results[0]
        if result.boxes is None:
            return []

        # Extrai caixas, confianças e classes
        boxes = result.boxes.xyxy.cpu().numpy() if hasattr(result.boxes.xyxy, "cpu") else result.boxes.xyxy
        classes = result.boxes.cls.cpu().numpy().astype(int) if hasattr(result.boxes.cls, "cpu") else result.boxes.cls.astype(int)
        confidences = result.boxes.conf.cpu().numpy() if hasattr(result.boxes.conf, "cpu") else result.boxes.conf

        people_detections = []
        epi_detections = []
        vehicles_detections = []

        # Categoriza as detecções do frame
        for box, cls_id, conf in zip(boxes, classes, confidences):
            label = self.class_to_label.get(cls_id)
            if label == "person":
                people_detections.append((box, conf))
            elif label in self.required_epis or label in {"mask", "gloves"}:
                epi_detections.append((box, label, conf))
            elif label == "vehicle":
                vehicles_detections.append((box, conf))

        events = []

        # 1. Auditoria de EPIs para cada pessoa detectada
        for p_box, p_conf in people_detections:
            worn_epis = set()
            for epi_box, epi_label, epi_conf in epi_detections:
                if self._check_overlap(epi_box, p_box):
                    worn_epis.add(epi_label)

            # Verifica quais itens obrigatórios estão ausentes
            missing_epis = [epi for epi in self.required_epis if epi not in worn_epis]

            if missing_epis:
                msg = f"Violação de Biossegurança: Pessoa detectada na barreira sem EPI obrigatório: {', '.join(missing_epis)}."
                metadata = {
                    "missing_epis": missing_epis,
                    "worn_epis": list(worn_epis),
                    "person_confidence": float(p_conf),
                }
                
                # Emite log crítico
                _log_event(
                    event_type="EPI_VIOLATION",
                    level="critical",
                    message=msg,
                    metadata=metadata,
                )
                
                events.append({
                    "event_type": "EPI_VIOLATION",
                    "level": "critical",
                    "message": msg,
                    "metadata": metadata,
                    "timestamp": time.time(),
                })

        # 2. Auditoria de Veículos
        for v_box, v_conf in vehicles_detections:
            msg = f"Auditoria de Barreira: Veículo detectado na entrada da zona {camera_zone}."
            metadata = {
                "vehicle_confidence": float(v_conf),
                "box": v_box.tolist(),
            }
            
            # Emite log crítico para monitoramento rígido de veículos
            _log_event(
                event_type="VEHICLE_DETECTION",
                level="critical",
                message=msg,
                metadata=metadata,
            )
            
            events.append({
                "event_type": "VEHICLE_DETECTION",
                "level": "critical",
                "message": msg,
                "metadata": metadata,
                "timestamp": time.time(),
            })

        return events

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok" if self.model is not None else "warning",
            "model_path": self.model_path,
            "required_epis": self.required_epis,
        }


def register():
    return BiosafetyAuditPlugin()
