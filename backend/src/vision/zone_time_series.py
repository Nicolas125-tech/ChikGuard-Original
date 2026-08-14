import time
import threading
from typing import List, Dict, Any


class ZoneTimeSeriesTracker:
    """
    Registrador de Séries Temporais de Permanência por Zona (Saltoratto et al., 2013).
    Gera o histórico F_stay(t) = (t, N_bebedouro, N_luz, N_comedouro) e o somatório cumulativo
    representados nas Figuras 20, 21 e 22 do artigo científico.
    """

    def __init__(self, max_history_len: int = 1440):
        self.max_history_len = max_history_len
        self._lock = threading.Lock()
        self._series: List[Dict[str, Any]] = []

    def record_sample(
        self,
        drinker_count: int,
        brooder_count: int,
        feeder_count: int,
        timestamp: float = None,
    ):
        """
        Registra uma amostra temporal da contagem de aves por zona.
        """
        ts = timestamp if timestamp is not None else time.time()
        
        sample = {
            "timestamp": ts,
            "drinker": drinker_count,
            "brooder": brooder_count,
            "feeder": feeder_count,
            "total": drinker_count + brooder_count + feeder_count,
        }

        with self._lock:
            self._series.append(sample)
            if len(self._series) > self.max_history_len:
                self._series.pop(0)

    def get_time_series(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retorna as últimas `limit` amostras registradas para alimentar gráficos.
        """
        with self._lock:
            return list(self._series[-limit:])

    def get_cumulative_summary(self) -> Dict[str, Any]:
        """
        Calcula o somatório total das frequências de permanência (Figura 22 do artigo).
        """
        with self._lock:
            if not self._series:
                return {
                    "total_samples": 0,
                    "cumulative_drinker": 0,
                    "cumulative_brooder": 0,
                    "cumulative_feeder": 0,
                    "most_frequented_zone": "NENHUMA",
                }

            sum_d = sum(s["drinker"] for s in self._series)
            sum_b = sum(s["brooder"] for s in self._series)
            sum_f = sum(s["feeder"] for s in self._series)

            counts_map = {"BEBEDOURO": sum_d, "AQUECIMENTO": sum_b, "COMEDOURO": sum_f}
            most_frequented = max(counts_map, key=counts_map.get)

            return {
                "total_samples": len(self._series),
                "cumulative_drinker": sum_d,
                "cumulative_brooder": sum_b,
                "cumulative_feeder": sum_f,
                "most_frequented_zone": most_frequented,
            }
