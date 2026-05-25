from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from database import db, SensorReading, BirdSnapshot, AcousticReading, EventLog, BatchLogbook, Batch
import json

class ChikGuardAgent:
    """Classe base abstrata para os agentes inteligentes do ChikGuard."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o ciclo de raciocínio e ação do agente.

        Args:
            context: Dicionário contendo dados de contexto adicionais (ex: limits, custom configs)

        Returns:
            Dict com o resultado da execução.
        """
        raise NotImplementedError("Cada agente deve implementar seu próprio método run.")


class VetWelfareAgent(ChikGuardAgent):
    """Agente Veterinário e de Bem-Estar Animal.

    Analisa o histórico recente de sensores físicos, telemetria de áudio acústico
    e eventos de comportamento/anomalias visuais para gerar um diagnóstico de bem-estar.
    """
    def __init__(self):
        super().__init__(
            name="VetWelfareAgent",
            description="Analisa a saúde, comportamento e bem-estar do lote correlacionando áudio, visão e sensores físicos."
        )

    def fetch_telemetry(self, hours: int = 4) -> Dict[str, Any]:
        """Coleta toda a telemetria relevante das últimas horas do banco de dados."""
        # Usamos UTC ingênuo para alinhar com o padrão de data e hora do banco do backend
        time_limit = datetime.utcnow() - timedelta(hours=hours)

        # 1. Sensores Físicos (Temperatura, Umidade, Amônia)
        sensors = SensorReading.query.filter(SensorReading.timestamp >= time_limit).all()
        
        # 2. Leituras Acústicas (Tosse, Estresse Respiratório, Estresse Sonoro)
        acoustics = AcousticReading.query.filter(AcousticReading.timestamp >= time_limit).all()

        # 3. Alertas visuais e anomalias registradas no EventLog
        critical_event_types = [
            "behavior_alert", 
            "prostration_alert", 
            "immobility_alert", 
            "carcass_alert", 
            "thermal_anomaly_alert"
        ]
        events = EventLog.query.filter(
            EventLog.timestamp >= time_limit,
            EventLog.event_type.in_(critical_event_types)
        ).all()

        # 4. Métricas de atividade agregadas pela visão computacional
        metrics = EventLog.query.filter(
            EventLog.timestamp >= time_limit,
            EventLog.event_type == "vision_metrics"
        ).all()

        return {
            "sensors": [s.to_dict() for s in sensors],
            "acoustics": [a.to_dict() for a in acoustics],
            "events": [e.to_dict() for e in events],
            "metrics": [m.to_dict() for m in metrics]
        }

    def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Processa a telemetria recente e infere o estado de bem-estar do lote.

        Se encontrar anomalias severas, registra automaticamente uma nota clínica
        no BatchLogbook do lote ativo.
        """
        if context is None:
            context = {}
            
        hours = context.get("hours", 4)
        telemetry = self.fetch_telemetry(hours=hours)

        # A. Processamento de Sensores Físicos
        temp_readings = [s["temperature_c"] for s in telemetry["sensors"] if s["temperature_c"] is not None]
        humi_readings = [s["humidity_pct"] for s in telemetry["sensors"] if s["humidity_pct"] is not None]
        amon_readings = [s["ammonia_ppm"] for s in telemetry["sensors"] if s["ammonia_ppm"] is not None]

        avg_temp = sum(temp_readings) / len(temp_readings) if temp_readings else 25.0
        avg_humi = sum(humi_readings) / len(humi_readings) if humi_readings else 60.0
        avg_amon = sum(amon_readings) / len(amon_readings) if amon_readings else 5.0

        # B. Processamento de Acústica
        resp_readings = [a["respiratory_health_index"] for a in telemetry["acoustics"]]
        cough_readings = [a["cough_index"] for a in telemetry["acoustics"]]
        stress_audio_readings = [a["stress_audio_index"] for a in telemetry["acoustics"]]

        avg_resp = sum(resp_readings) / len(resp_readings) if resp_readings else 1.0
        avg_cough = sum(cough_readings) / len(cough_readings) if cough_readings else 0.0
        avg_stress_audio = sum(stress_audio_readings) / len(stress_audio_readings) if stress_audio_readings else 0.0

        # C. Contagem e Agrupamento de Eventos Críticos
        carcass_count = sum(1 for e in telemetry["events"] if e["event_type"] == "carcass_alert")
        prostration_count = sum(1 for e in telemetry["events"] if e["event_type"] == "prostration_alert")
        immobility_count = sum(1 for e in telemetry["events"] if e["event_type"] == "immobility_alert")
        behavior_count = sum(1 for e in telemetry["events"] if e["event_type"] == "behavior_alert")
        thermal_anomaly_count = sum(1 for e in telemetry["events"] if e["event_type"] == "thermal_anomaly_alert")

        # D. Diagnóstico e Regras de Decisão
        welfare_status = "NORMAL"
        anomalies = []
        recommendations = []

        # 1. Regra para Amônia (Alta toxicidade)
        if avg_amon > 20.0:
            welfare_status = "CRITICAL"
            anomalies.append(f"Nível de amônia perigosamente alto: {avg_amon:.1f} ppm (Limite sugerido: 20 ppm).")
            recommendations.append("Ligar ventilação máxima imediatamente para renovar o ar.")
        elif avg_amon > 15.0:
            if welfare_status != "CRITICAL":
                welfare_status = "WARNING"
            anomalies.append(f"Amônia elevada: {avg_amon:.1f} ppm.")
            recommendations.append("Aumentar ciclos de ventilação e checar se há acúmulo de umidade na cama aviária.")

        # 2. Regra para Saúde Acústica
        if avg_cough > 0.5 or avg_resp < 0.7:
            welfare_status = "CRITICAL"
            anomalies.append(f"Detecção de estresse acústico/tosse: Tosse={avg_cough:.2f}, RespHealth={avg_resp:.2f}.")
            recommendations.append("Avaliar urgentemente a saúde respiratória do lote. Possível surto de bronquite ou colibacilose.")
        elif avg_stress_audio > 0.6:
            if welfare_status != "CRITICAL":
                welfare_status = "WARNING"
            anomalies.append(f"Estresse sonoro elevado (vocalizações de pânico/alarme): {avg_stress_audio:.2f}.")
            recommendations.append("Investigar potenciais fontes de estresse físico, predadores externos, ou ruídos mecânicos anômalos.")

        # 3. Regra para Eventos da Visão Computacional (Dead Birds, Inatividade)
        if carcass_count > 0:
            welfare_status = "CRITICAL"
            anomalies.append(f"Detecção de {carcass_count} alerta(s) de carcaça (aves mortas) na análise recente.")
            recommendations.append("Realizar remoção manual imediata das aves mortas para evitar contaminações.")
        
        if (prostration_count + immobility_count) > 5:
            if welfare_status != "CRITICAL":
                welfare_status = "WARNING"
            anomalies.append(f"Alto índice de aves prostradas ou imóveis: {prostration_count + immobility_count} avistamentos.")
            recommendations.append("Verificar o conforto térmico local ou possíveis sintomas clínicos de apatia infecciosa.")

        if behavior_count > 3:
            # Amontoamento ou distribuição espacial atípica
            if welfare_status == "NORMAL":
                welfare_status = "WARNING"
            anomalies.append(f"Anomalias de comportamento espacial/agrupamento recorrentes ({behavior_count} alertas).")
            recommendations.append("Verificar a uniformidade térmica do galpão (correntes de vento frio direcionais).")

        # Conclusão e Resumo
        summary_text = (
            f"[Diagnóstico Veterinário - {welfare_status}]\n"
            f"Sensores: Temp={avg_temp:.1f}°C, Umid={avg_humi:.1f}%, Amônia={avg_amon:.1f}ppm\n"
            f"Saúde Acústica: Resp={avg_resp:.2f}, Tosse={avg_cough:.2f}, Estresse={avg_stress_audio:.2f}\n"
            f"Métricas Visuais: Carcaças={carcass_count}, Prostradas={prostration_count}, Agrupamento={behavior_count}\n"
        )
        if anomalies:
            summary_text += "Anomalias Detectadas:\n" + "\n".join([f"- {a}" for a in anomalies]) + "\n"
            summary_text += "Ações Recomendadas:\n" + "\n".join([f"- {r}" for r in recommendations])
        else:
            summary_text += "Lote saudável e confortável. Nenhuma ação recomendada."

        # E. Gravar no BatchLogbook caso existam anomalias ou o status seja de alerta
        # Buscamos o lote ativo para linkar a nota
        active_batch = Batch.query.filter(Batch.active == True).first()
        batch_id = active_batch.id if active_batch else None
        
        # Só registramos no diário se houver alguma anomalia/aviso relevante
        log_created = False
        if welfare_status in ["WARNING", "CRITICAL"] or context.get("force_log", False):
            try:
                log_entry = BatchLogbook(
                    camera_id=context.get("camera_id", "galpao-1"),
                    batch_id=batch_id,
                    note=summary_text,
                    author="Agent_VetWelfare",
                    timestamp=datetime.utcnow()
                )
                db.session.add(log_entry)
                db.session.commit()
                log_created = True
            except Exception as e:
                db.session.rollback()
                # Não propagamos erro se falhar apenas a gravação da nota para não travar o fluxo
                summary_text += f"\n[Erro ao salvar nota no banco: {str(e)}]"

        return {
            "agent": self.name,
            "status": "COMPLETED",
            "welfare_status": welfare_status,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "summary": summary_text,
            "logbook_entry_created": log_created,
            "timestamp": datetime.utcnow().isoformat()
        }
