import time
import math
import numpy as np
from typing import List, Tuple, Dict, Any


class TriZoneBehaviorAnalyzer:
    """
    Analisador de Zonamento Trifásico & Frequência de Permanência (Saltoratto et al., 2013).
    
    Divisão funcional da baia:
      1. Zona (a) Bebedouro (Drinker / Azul): (0.00 a 0.33 na largura da baia).
      2. Zona (b) Luz de Aquecimento / Campânula (Brooder Light / Vermelha): (0.33 a 0.66 na largura).
      3. Zona (c) Comedouro (Feeder / Verde): (0.66 a 1.00 na largura da baia).
      
    Regras de Negócio de Bem-Estar Animal:
      • Se a permanência na Zona de Aquecimento for > 60%: Indica dia frio / arrefecimento da baia (Estresse por Frio).
      • Se a permanência na Zona Bebedouro for > 50%: Indica aquecimento excessivo / desidratação (Estresse Calórico).
      • Se houver distribuição equilibrada entre Comedouro, Bebedouro e Aquecimento: Conforto Térmico & Bem-Estar Ideal.
    """

    def __init__(self, window_size: int = 300):
        self.window_size = window_size
        self._stay_history: List[Dict[str, Any]] = []

    def analyze_zones(
        self,
        bird_centers: List[Tuple[float, float]],
        frame_width: int,
        frame_height: int,
        timestamp: float = None,
    ) -> Dict[str, Any]:
        """
        Classifica cada ave nas 3 zonas e calcula as estatísticas de permanência e conforto térmico.
        """
        ts = timestamp if timestamp is not None else time.time()
        
        drinker_count = 0  # Zona (a) Bebedouro - Azul
        brooder_count = 0  # Zona (b) Luz de Aquecimento - Vermelha
        feeder_count = 0   # Zona (c) Comedouro - Verde

        if bird_centers and frame_width > 0:
            for cx, cy in bird_centers:
                x_norm = cx / float(frame_width)
                if x_norm < 0.33:
                    drinker_count += 1
                elif x_norm < 0.66:
                    brooder_count += 1
                else:
                    feeder_count += 1

        tot = drinker_count + brooder_count + feeder_count
        drinker_pct = round(drinker_count / max(1, tot), 2)
        brooder_pct = round(brooder_count / max(1, tot), 2)
        feeder_pct = round(feeder_count / max(1, tot), 2)

        # Regra de Negócio de Conforto Térmico & Bem-Estar Animal
        if tot > 0 and brooder_pct >= 0.60:
            welfare_status = "ESTRESSE_FRIO"
            welfare_message = "Alerta de Ambiência: Pintainhos agrupados na luz de aquecimento (baixa temperatura / dia frio)"
            welfare_index = round(1.0 - brooder_pct, 2)
        elif tot > 0 and drinker_pct >= 0.50:
            welfare_status = "ESTRESSE_CALOR"
            welfare_message = "Alerta de Ambiência: Concentração elevada no bebedouro (alta temperatura / sede)"
            welfare_index = round(1.0 - drinker_pct, 2)
        else:
            welfare_status = "CONFORTO_IDEAL"
            welfare_message = "Ambiência Adequada: Distribuição homogênea entre comedouro, bebedouro e aquecimento"
            welfare_index = 0.95

        entry = {
            "timestamp": ts,
            "drinker_count": drinker_count,
            "brooder_count": brooder_count,
            "feeder_count": feeder_count,
            "drinker_pct": drinker_pct,
            "brooder_pct": brooder_pct,
            "feeder_pct": feeder_pct,
            "welfare_status": welfare_status,
            "welfare_message": welfare_message,
            "welfare_index": welfare_index,
            "total_birds": tot,
        }

        self._stay_history.append(entry)
        if len(self._stay_history) > self.window_size:
            self._stay_history.pop(0)

        return entry

    def get_stay_frequency_summary(self) -> Dict[str, Any]:
        """
        Retorna o somatório cumulativo das frequências de permanência por zona (Figura 22 do artigo).
        """
        if not self._stay_history:
            return {
                "total_samples": 0,
                "sum_drinker": 0,
                "sum_brooder": 0,
                "sum_feeder": 0,
                "avg_welfare_index": 1.0,
            }

        sum_d = sum(e["drinker_count"] for e in self._stay_history)
        sum_b = sum(e["brooder_count"] for e in self._stay_history)
        sum_f = sum(e["feeder_count"] for e in self._stay_history)
        avg_w = float(np.mean([e["welfare_index"] for e in self._stay_history]))

        return {
            "total_samples": len(self._stay_history),
            "sum_drinker": sum_d,
            "sum_brooder": sum_b,
            "sum_feeder": sum_f,
            "avg_welfare_index": round(avg_w, 2),
        }
