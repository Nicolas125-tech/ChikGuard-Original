import time
# from backend.database import db # Assuming a generic db setup, might need adjustment based on actual models
# Note: In a real implementation, you would import the specific SQLAlchemy model

class AnalyticsEngine:
    """
    Exporta métricas de densidade e atividade para a base de dados
    """
    def __init__(self, export_interval_seconds=60):
        self.export_interval = export_interval_seconds
        self.last_export_time = time.time()
        self._activity_buffer = []
        self._density_buffer = []

    def log_metrics(self, density, activity_pixels_per_sec):
        """Acumula métricas no buffer"""
        self._density_buffer.append(density)
        self._activity_buffer.append(activity_pixels_per_sec)

        current_time = time.time()
        if current_time - self.last_export_time >= self.export_interval:
            self.export_to_database()
            self.last_export_time = current_time

    def export_to_database(self):
        """Calcula médias e salva no DB (mock for now, replace with actual DB call)"""
        if not self._density_buffer or not self._activity_buffer:
            return

        avg_density = sum(self._density_buffer) / len(self._density_buffer)
        avg_activity = sum(self._activity_buffer) / len(self._activity_buffer)

        print(f"[Analytics] Exportando: Densidade Media={avg_density:.2f}, Atividade Media={avg_activity:.2f} px/s")

        # Here you would typically do:
        # new_metric = MetricModel(density=avg_density, activity=avg_activity)
        # db.session.add(new_metric)
        # db.session.commit()

        # Limpar buffers após exportar
        self._density_buffer = []
        self._activity_buffer = []
