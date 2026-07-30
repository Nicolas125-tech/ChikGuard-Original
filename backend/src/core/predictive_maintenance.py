import time
import logging
from src.core.state import sensor_state, sensor_thresholds
from src.api.fastapi_ws import emit_new_alert

logger = logging.getLogger(__name__)

# Memoria de estados para a Manutencao Preditiva
predictive_memory = {
    "fan_turned_on_at": None,
    "temp_when_fan_turned_on": None,
    "heater_turned_on_at": None,
    "temp_when_heater_turned_on": None,
    "last_anomaly_alert": 0
}

# Parametros de diagnostico
EVALUATION_WINDOW_SEC = 120  # 2 minutos para avaliar se o atuador surtiu efeito
EXPECTED_TEMP_DELTA = 0.5    # Espera-se que a temperatura mude pelo menos 0.5C em 2 mins
ALERT_COOLDOWN_SEC = 300     # Nao enviar spam de alertas do mesmo erro

async def run_predictive_diagnostics(actuator_state):
    """
    Analisa se as acoes dos atuadores (ligar fan/heater) estao realmente 
    causando mudanca nos sensores termicos. Se nao, ha falha de hardware.
    """
    now = time.time()
    current_temp = sensor_state.get("temperature_c", 25.0)
    
    # --- Diagnostico do Ventilador ---
    if actuator_state.get("ventilacao_on"):
        if predictive_memory["fan_turned_on_at"] is None:
            # Acabou de ligar
            predictive_memory["fan_turned_on_at"] = now
            predictive_memory["temp_when_fan_turned_on"] = current_temp
        else:
            # Ja esta ligado, vamos ver ha quanto tempo
            elapsed = now - predictive_memory["fan_turned_on_at"]
            if elapsed > EVALUATION_WINDOW_SEC:
                # O ventilador esta ligado ha X minutos. A temperatura baixou?
                start_temp = predictive_memory["temp_when_fan_turned_on"]
                # Só alerta se a temperatura atual ainda estiver acima da zona de conforto confortável (> 24°C)
                if current_temp >= (start_temp - 0.2) and current_temp > 24.0:
                    if now - predictive_memory["last_anomaly_alert"] > ALERT_COOLDOWN_SEC:
                        logger.error("Falha de Hardware Detectada: Ventilador LIGADO, mas temperatura NAO BAIXA!")
                        predictive_memory["last_anomaly_alert"] = now
                        await emit_new_alert({
                            "type": "hardware_anomaly",
                            "level": "critical",
                            "component": "Exaustor/Ventilador",
                            "message": f"Alerta de Falha: O ventilador está ligado há {int(elapsed/60)} min, mas a temperatura de {current_temp:.1f}°C não está caindo. Verifique o motor ou correia do equipamento!",
                            "timestamp": now
                        })
                # Reseta o baseline para a próxima janela de avaliação contínua (evita congelamento do estado de referência)
                predictive_memory["fan_turned_on_at"] = now
                predictive_memory["temp_when_fan_turned_on"] = current_temp
    else:
        # Reseta a memoria do ventilador se ele foi desligado
        predictive_memory["fan_turned_on_at"] = None
        predictive_memory["temp_when_fan_turned_on"] = None

    # --- Diagnostico do Aquecedor ---
    if actuator_state.get("aquecedor_on"):
        if predictive_memory["heater_turned_on_at"] is None:
            # Acabou de ligar
            predictive_memory["heater_turned_on_at"] = now
            predictive_memory["temp_when_heater_turned_on"] = current_temp
        else:
            elapsed = now - predictive_memory["heater_turned_on_at"]
            if elapsed > EVALUATION_WINDOW_SEC:
                # O aquecedor esta ligado ha X minutos. A temperatura subiu?
                start_temp = predictive_memory["temp_when_heater_turned_on"]
                # Só alerta se o galpão ainda estiver frio (< 25°C)
                if current_temp <= (start_temp + 0.2) and current_temp < 25.0:
                    if now - predictive_memory["last_anomaly_alert"] > ALERT_COOLDOWN_SEC:
                        logger.error("Falha de Hardware Detectada: Aquecedor LIGADO, mas temperatura NAO SOBE!")
                        predictive_memory["last_anomaly_alert"] = now
                        await emit_new_alert({
                            "type": "hardware_anomaly",
                            "level": "critical",
                            "component": "Aquecedor/Campânula",
                            "message": f"Alerta de Falha: O aquecedor está operando há {int(elapsed/60)} min, mas o galpão continua frio ({current_temp:.1f}°C). Falta de gás ou ignitor defeituoso?",
                            "timestamp": now
                        })
                # Reseta o baseline para a próxima janela de avaliação contínua (evita congelamento do estado de referência)
                predictive_memory["heater_turned_on_at"] = now
                predictive_memory["temp_when_heater_turned_on"] = current_temp
    else:
        # Reseta a memoria do aquecedor se ele foi desligado
        predictive_memory["heater_turned_on_at"] = None
        predictive_memory["temp_when_heater_turned_on"] = None
