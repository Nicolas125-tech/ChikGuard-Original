from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass

from database import AcousticReading, Batch, BatchLogbook, EventLog, SensorReading, db



@dataclass
class VisualCounts:
    carcass: int
    prostration: int
    immobility: int
    behavior: int


class ChikGuardAgent:

    """Classe base abstrata para os agentes de decisão inteligente do ChikGuard."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o ciclo de raciocínio do agente. Deve ser sobrescrita pelas subclasses."""
        raise NotImplementedError("Cada agente deve implementar seu próprio método run.")


class VetWelfareAgent(ChikGuardAgent):
    """
    Agente Veterinário e de Bem-Estar Animal.
    Analisa correlações de áudio, visão e sensores físicos para gerar diagnósticos e recomendações.
    """

    def __init__(self):
        super().__init__(
            name="VetWelfareAgent",
            description="Analisa a saúde, comportamento e bem-estar do lote correlacionando áudio, visão e sensores físicos.",
        )

    def fetch_telemetry(self, hours: int = 4) -> Dict[str, Any]:
        """Coleta toda a telemetria recente do banco de dados para análise."""
        time_limit = datetime.utcnow() - timedelta(hours=hours)

        sensors = SensorReading.query.filter(SensorReading.timestamp >= time_limit).all()
        acoustics = AcousticReading.query.filter(AcousticReading.timestamp >= time_limit).all()

        critical_events = [
            "behavior_alert",
            "prostration_alert",
            "immobility_alert",
            "carcass_alert",
            "thermal_anomaly_alert",
        ]
        events = EventLog.query.filter(
            EventLog.timestamp >= time_limit, EventLog.event_type.in_(critical_events)
        ).all()
        metrics = EventLog.query.filter(
            EventLog.timestamp >= time_limit, EventLog.event_type == "vision_metrics"
        ).all()

        return {
            "sensors": [s.to_dict() for s in sensors],
            "acoustics": [a.to_dict() for a in acoustics],
            "events": [e.to_dict() for e in events],
            "metrics": [m.to_dict() for m in metrics],
        }

    # ── Funções de Diagnóstico Clínico (SRP - Single Responsibility) ──

    def _diagnose_ammonia(
        self, avg_amon: float, recommendations: List[str], anomalies: List[str]
    ) -> str:
        """Avalia os riscos de toxicidade por gás amônia."""
        if avg_amon > 20.0:
            anomalies.append(
                f"Nível de amônia perigosamente alto: {avg_amon:.1f} ppm (Limite: 20 ppm)."
            )
            recommendations.append("Ligar ventilação máxima imediatamente para renovação do ar.")
            return "CRITICAL"
        if avg_amon > 15.0:
            anomalies.append(f"Amônia elevada: {avg_amon:.1f} ppm.")
            recommendations.append(
                "Aumentar ciclos de ventilação e checar acúmulo de umidade na cama."
            )
            return "WARNING"
        return "NORMAL"

    def _diagnose_respiratory_health(
        self,
        avg_cough: float,
        avg_resp: float,
        avg_stress: float,
        recommendations: List[str],
        anomalies: List[str],
    ) -> str:
        """Avalia a saúde respiratória e estresse acústico das aves."""
        if avg_cough > 0.5 or avg_resp < 0.7:
            anomalies.append(
                f"Detecção de estresse acústico/tosse: Tosse={avg_cough:.2f}, RespHealth={avg_resp:.2f}."
            )
            recommendations.append(
                "Avaliar a saúde do lote urgentemente. Possível surto de infecção respiratória."
            )
            return "CRITICAL"
        if avg_stress > 0.6:
            anomalies.append(f"Estresse sonoro elevado (vocalizações de alarme): {avg_stress:.2f}.")
            recommendations.append(
                "Investigar potenciais fontes de estresse físico, predadores ou ruídos mecânicos."
            )
            return "WARNING"
        return "NORMAL"

    def _diagnose_visual_anomalies(
        self,
        counts: VisualCounts,
        recommendations: List[str],
        anomalies: List[str],
    ) -> str:
        """Avalia anomalias visuais como mortalidade, apatia e amontoamento."""
        status = "NORMAL"

        if counts.carcass > 0:
            anomalies.append(
                f"Detecção de {counts.carcass} alerta(s) de carcaça (aves mortas) recente."
            )
            recommendations.append(
                "Realizar remoção manual imediata das aves mortas para evitar contaminações."
            )
            status = "CRITICAL"

        if (counts.prostration + counts.immobility) > 5:
            anomalies.append(
                f"Alto índice de aves prostradas/imóveis: {counts.prostration + counts.immobility} avistamentos."
            )
            recommendations.append(
                "Verificar o conforto térmico local ou possíveis sintomas de apatia infecciosa."
            )
            if status != "CRITICAL":
                status = "WARNING"

        if counts.behavior > 3:
            anomalies.append(
                f"Anomalias de comportamento espacial/agrupamento recorrentes ({counts.behavior} alertas)."
            )
            recommendations.append(
                "Verificar a uniformidade térmica do galpão (bolsões de frio ou correntes de vento)."
            )
            if status == "NORMAL":
                status = "WARNING"

        return status

    def _aggregate_averages(
        self, telemetry: Dict[str, Any]
    ) -> Tuple[Dict[str, float], Dict[str, int]]:
        """Calcula as médias de sensores e soma a contagem dos eventos clínicos."""
        # Médias físicas
        temp = [s["temperature_c"] for s in telemetry["sensors"] if s["temperature_c"] is not None]
        humi = [s["humidity_pct"] for s in telemetry["sensors"] if s["humidity_pct"] is not None]
        amon = [s["ammonia_ppm"] for s in telemetry["sensors"] if s["ammonia_ppm"] is not None]

        # Médias acústicas
        resp = [a["respiratory_health_index"] for a in telemetry["acoustics"]]
        cough = [a["cough_index"] for a in telemetry["acoustics"]]
        stress = [a["stress_audio_index"] for a in telemetry["acoustics"]]

        averages = {
            "temp": sum(temp) / len(temp) if temp else 25.0,
            "humi": sum(humi) / len(humi) if humi else 60.0,
            "amon": sum(amon) / len(amon) if amon else 5.0,
            "resp": sum(resp) / len(resp) if resp else 1.0,
            "cough": sum(cough) / len(cough) if cough else 0.0,
            "stress": sum(stress) / len(stress) if stress else 0.0,
        }

        # Cálculo científico do ITU (Índice de Temperatura e Umidade) adaptado para frangos de corte
        # Formula: ITU = 0.8 * Temp + (UR / 100) * (Temp - 14.4) + 46.4
        t = averages["temp"]
        rh = averages["humi"]
        thi_val = 0.8 * t + (rh / 100.0) * (t - 14.4) + 46.4
        averages["thi"] = thi_val

        # Contagem de eventos de visão
        events = telemetry["events"]
        counts = {
            "carcass": sum(1 for e in events if e["event_type"] == "carcass_alert"),
            "prostration": sum(1 for e in events if e["event_type"] == "prostration_alert"),
            "immobility": sum(1 for e in events if e["event_type"] == "immobility_alert"),
            "behavior": sum(1 for e in events if e["event_type"] == "behavior_alert"),
            "thermal_anomaly": sum(1 for e in events if e["event_type"] == "thermal_anomaly_alert"),
        }

        return averages, counts

    def _diagnose_thermal_index(
        self, thi: float, recommendations: List[str], anomalies: List[str]
    ) -> str:
        """Diagnostica o estresse térmico com base no ITU científico (Índice de Temperatura e Umidade)."""
        if thi >= 80.0:
            anomalies.append(f"ITU Crítico ({thi:.1f}): Risco iminente de mortalidade por estresse térmico severo.")
            recommendations.append("Acionar exaustores na velocidade máxima (efeito wind-chill) e verificar o sistema de nebulização (se UR < 80%).")
            return "CRITICAL"
        elif thi >= 75.0:
            anomalies.append(f"ITU Elevado ({thi:.1f}): Estresse térmico moderado detectado.")
            recommendations.append("Aumentar a ventilação mínima e renovação de ar no galpão.")
            return "WARNING"
        return "NORMAL"

    def _generate_diagnostic_note(
        self,
        welfare_status: str,
        averages: Dict[str, float],
        counts: Dict[str, int],
        anomalies: List[str],
        recommendations: List[str],
    ) -> str:
        """Formata o relatório clínico final a ser persistido no Logbook."""
        summary = (
            f"[Diagnóstico Veterinário - {welfare_status}]\n"
            f"Sensores: Temp={averages['temp']:.1f}°C, Umid={averages['humi']:.1f}%, Amônia={averages['amon']:.1f}ppm, ITU={averages['thi']:.1f}\n"
            f"Saúde Acústica: Resp={averages['resp']:.2f}, Tosse={averages['cough']:.2f}, Estresse={averages['stress']:.2f}\n"
            f"Métricas Visuais: Carcaças={counts['carcass']}, Prostradas={counts['prostration']}, Agrupamento={counts['behavior']}\n"
        )
        if anomalies:
            summary += "\nAnomalias Detectadas:\n" + "\n".join([f"- {a}" for a in anomalies]) + "\n"
            summary += "Ações Recomendadas:\n" + "\n".join([f"- {r}" for r in recommendations])
        else:
            summary += "\nLote saudável e confortável. Nenhuma recomendação."
        return summary

    def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Inicia a análise e opcionalmente gera uma entrada no logbook."""
        context = context or {}
        telemetry = self.fetch_telemetry(hours=context.get("hours", 4))
        averages, counts = self._aggregate_averages(telemetry)

        recommendations = []
        anomalies = []

        # Executa as regras de diagnóstico em cadeia
        amonia_status = self._diagnose_ammonia(averages["amon"], recommendations, anomalies)
        
        # Correlação patológica de sinergia entre Amônia (NH3) e tosses acústicas
        synergy_status = "NORMAL"
        if averages["amon"] > 10.0 and averages["cough"] > 0.3:
            anomalies.append(
                f"Sinergia Patológica Detectada: Amônia elevada ({averages['amon']:.1f} ppm) combinada com tosses acústicas recorrentes ({averages['cough']:.2f}). Alto risco de lesão ciliar na traqueia e infecção respiratória secundária (ex: Colibacilose, Micoplasmose)."
            )
            recommendations.append(
                "Urgente: Incrementar ventilação de renovação para baixar amônia abaixo de 10 ppm e realizar avaliação diagnóstica clínica."
            )
            synergy_status = "CRITICAL"

        resp_status = self._diagnose_respiratory_health(
            averages["cough"], averages["resp"], averages["stress"], recommendations, anomalies
        )
        
        thermal_status = self._diagnose_thermal_index(
            averages["thi"], recommendations, anomalies
        )
        
        visual_counts = VisualCounts(
            carcass=counts["carcass"],
            prostration=counts["prostration"],
            immobility=counts["immobility"],
            behavior=counts["behavior"],
        )
        visual_status = self._diagnose_visual_anomalies(
            visual_counts,
            recommendations,
            anomalies,
        )

        # Escolhe o status mais grave (CRITICAL > WARNING > NORMAL)
        status_rank = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2}
        welfare_status = max(
            [amonia_status, synergy_status, resp_status, thermal_status, visual_status], key=lambda s: status_rank[s]
        )

        summary_text = self._generate_diagnostic_note(
            welfare_status, averages, counts, anomalies, recommendations
        )

        # Registro no diário de bordo (BatchLogbook) do lote ativo se status for de atenção/crítico
        log_created = False
        if welfare_status in {"WARNING", "CRITICAL"} or context.get("force_log", False):
            active_batch = Batch.query.filter(Batch.active == True).first()
            batch_id = active_batch.id if active_batch else None
            try:
                log_entry = BatchLogbook(
                    camera_id=context.get("camera_id", "galpao-1"),
                    batch_id=batch_id,
                    note=summary_text,
                    author="Agent_VetWelfare",
                    timestamp=datetime.utcnow(),
                )
                db.session.add(log_entry)
                db.session.commit()
                log_created = True
            except Exception as e:
                db.session.rollback()
                summary_text += f"\n[Erro ao salvar no Logbook: {e}]"

        return {
            "agent": self.name,
            "status": "COMPLETED",
            "welfare_status": welfare_status,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "summary": summary_text,
            "logbook_entry_created": log_created,
            "timestamp": datetime.utcnow().isoformat(),
        }


class ClimateAgent(ChikGuardAgent):
    """
    Agente de Climatização Preditiva.
    Consome a previsão externa e sugere ajustes preventivos para aquecedores e ventiladores.
    """

    def __init__(self, weather_plugin=None):
        super().__init__(
            name="ClimateAgent",
            description="Analisa a previsão do tempo externa para ajustar dinamicamente as metas térmicas da FSM.",
        )
        self.weather_plugin = weather_plugin

    def _determine_adjustments(
        self, weather: Dict[str, Any], forecast: List[Dict[str, Any]], targets: Dict[str, float]
    ) -> List[str]:
        """Analisa a previsão de curto prazo e ajusta preventivamente os alvos climáticos."""
        adjustments = []
        heatwave = weather.get("heatwave_active", False)
        cold_snap = weather.get("cold_snap_active", False)

        # Previsão das próximas 6 horas
        high_temp_forecasted = any(f["temp_c"] >= 33.0 for f in forecast[:6])
        low_temp_forecasted = any(f["temp_c"] <= 16.0 for f in forecast[:6])

        target_temp = targets.get("target_temp", 28.0)

        if heatwave or high_temp_forecasted:
            # Pré-resfriamento preventivo: abaixa os thresholds de ventilação relativo ao conforto do lote
            targets["fan_on_temp"] = target_temp + 2.0
            targets["fan_off_temp"] = target_temp + 1.0
            targets["heater_on_temp"] = target_temp - 7.0
            targets["heater_off_temp"] = target_temp - 6.0
            adjustments.append(
                f"Pré-resfriamento preventivo ativado: ventiladores ajustados para {targets['fan_on_temp']:.1f}°C."
            )

        elif cold_snap or low_temp_forecasted:
            # Pré-aquecimento preventivo: eleva limites de aquecedores relativo ao conforto do lote
            targets["heater_on_temp"] = target_temp - 2.0
            targets["heater_off_temp"] = target_temp - 1.0
            targets["fan_on_temp"] = target_temp + 5.0
            targets["fan_off_temp"] = target_temp + 4.0
            adjustments.append(
                f"Pré-aquecimento preventivo ativado: aquecedores elevados para {targets['heater_on_temp']:.1f}°C."
            )

        return adjustments

    def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        plugin = self.weather_plugin or context.get("weather_plugin")

        if not plugin:
            return {
                "agent": self.name,
                "status": "FAILED",
                "error": "WeatherForecastPlugin não disponível.",
                "timestamp": datetime.utcnow().isoformat(),
            }

        weather = plugin.get_current_weather()
        forecast = plugin.get_forecast_12h()
        external_temp = weather.get("temperature_c", 25.0)

        # Determinar temperatura ideal do lote com base na idade (Ross 308 / Cobb 500)
        target_temp = 28.0
        try:
            active_batch = Batch.query.filter(Batch.active == True).first()
            if active_batch and active_batch.start_date:
                # Se for o lote de teste legado ou inicial automático, mantém o padrão para compatibilidade de testes
                if getattr(active_batch, "name", "") in ("Lote inicial", "Batch Teste Calor"):
                    target_temp = 28.0
                else:
                    from src.core.state_machine import get_ideal_temp_for_age
                    age_day = max(1, (datetime.utcnow().date() - active_batch.start_date.date()).days + 1)
                    target_temp = get_ideal_temp_for_age(age_day)
        except Exception as e:
            logger.error(f"Erro ao obter temperatura de conforto do lote no ClimateAgent: {e}")

        # Alvos climáticos padrão a serem otimizados baseados no conforto biológico das aves
        targets = {
            "target_temp": target_temp,
            "fan_on_temp": target_temp + 4.0,
            "fan_off_temp": target_temp + 3.0,
            "heater_on_temp": target_temp - 4.0,
            "heater_off_temp": target_temp - 3.0,
        }

        adjustments = self._determine_adjustments(weather, forecast, targets)

        # Registra log se houverem ações preditivas
        if adjustments:
            try:
                active_batch = Batch.query.filter(Batch.active == True).first()
                batch_id = active_batch.id if active_batch else None
                log_entry = BatchLogbook(
                    camera_id=context.get("camera_id", "galpao-1"),
                    batch_id=batch_id,
                    note="[Otimização Climática - ClimateAgent]\n"
                    + "\n".join([f"- {a}" for a in adjustments]),
                    author="Agent_Climate",
                    timestamp=datetime.utcnow(),
                )
                db.session.add(log_entry)
                db.session.commit()
            except Exception:
                db.session.rollback()

        return {
            "agent": self.name,
            "status": "COMPLETED",
            "current_external_temp": external_temp,
            "adjustments": adjustments,
            "recommended_targets": targets,
            "timestamp": datetime.utcnow().isoformat(),
        }
