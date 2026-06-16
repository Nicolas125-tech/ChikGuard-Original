import asyncio
import time
import logging
from src.core.state_machine import BusinessStateMachine
from src.core.state import sensor_state, sensor_thresholds
from src.api.fastapi_ws import emit_new_alert

logger = logging.getLogger(__name__)

# Instancia global da Maquina de Estados
fsm = BusinessStateMachine()

# Variaveis de estado global dos atuadores 
actuator_state = {
    "ventilacao_on": False,
    "aquecedor_on": False,
}

async def fsm_loop():
    """Loop continuo que reage a sensores e executa acoes baseadas nas regras de FSM."""
    logger.info("Iniciando FSM Autonoma em Background (FastAPI)")
    
    while True:
        try:
            # Puxa o contexto do que esta acontecendo agora
            context = {
                "temp_atual": sensor_state["temperature_c"],
                "ventilacao_on": actuator_state["ventilacao_on"],
                "aquecedor_on": actuator_state["aquecedor_on"],
                "hour": time.localtime().tm_hour,
                "targets": {
                    "fan_on_temp": sensor_thresholds["temp_max"],
                    "fan_off_temp": sensor_thresholds["temp_max"] - 1.0,
                    "heater_on_temp": sensor_thresholds["temp_min"],
                    "heater_off_temp": sensor_thresholds["temp_min"] + 1.0,
                    "batch_age_day": 21 # Em prod buscaria do banco de dados (Batch)
                },
                "intrusion_active": False, # Placeholder
                "preheat_recommended": False
            }
            
            # Submete o cenario para a AI (FSM)
            result = fsm.process_context(context)
            
            # Se a FSM mandar alterar algo, aplicar fisicamente (simulado via state por enquanto)
            if result["changes"]:
                for change in result["changes"]:
                    logger.warning(f"FSM Acao: {change} | Motivo (Estado): {result['state']}")
                    
                    # Notificar o dashboard em tempo real via WebSocket!
                    await emit_new_alert({
                        "type": "actuator_change",
                        "level": "info",
                        "message": f"Mudança autônoma: {change}",
                        "timestamp": time.time()
                    })

                actuator_state["ventilacao_on"] = result["ventilacao"]
                actuator_state["aquecedor_on"] = result["aquecedor"]
                
            # --- MANUTENCAO PREDITIVA (Verificacao de Falha de Hardware) ---
            from src.core.predictive_maintenance import run_predictive_diagnostics
            await run_predictive_diagnostics(actuator_state)
            
        except Exception as e:
            logger.error(f"Erro critico na FSM Loop: {e}")
            
        # O FSM processa a cada 5 segundos de forma assincrona sem bloquear a web api
        await asyncio.sleep(5)
