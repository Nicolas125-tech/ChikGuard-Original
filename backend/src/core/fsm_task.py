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
            # Busca lote ativo no banco de dados para calcular a idade real do lote e as metas zootécnicas
            from src.db.session import SessionLocal
            from database import Batch
            from datetime import datetime
            from src.core.state_machine import get_ideal_temp_for_age

            db_session = SessionLocal()
            batch_age_day = 21
            target_temp = 23.0
            try:
                batch = db_session.query(Batch).filter_by(camera_id="galpao-1", active=True).order_by(Batch.id.desc()).first()
                if batch:
                    batch_age_day = max(1, (datetime.utcnow().date() - batch.start_date.date()).days + 1)
                target_temp = get_ideal_temp_for_age(batch_age_day)
            except Exception as db_err:
                logger.error(f"Erro ao buscar lote ativo na FSM: {db_err}")
                target_temp = get_ideal_temp_for_age(batch_age_day)
            finally:
                db_session.close()

            # Limites e diferenciais de acionamento dinâmicos e adequados
            heater_on = max(15.0, target_temp - 0.5)
            heater_off = max(15.0, target_temp + 0.2)
            fan_on = min(38.0, target_temp + 2.0)
            fan_off = min(38.0, target_temp + 1.0)

            # Puxa o contexto do que esta acontecendo agora
            context = {
                "temp_atual": sensor_state["temperature_c"],
                "ventilacao_on": actuator_state["ventilacao_on"],
                "aquecedor_on": actuator_state["aquecedor_on"],
                "hour": time.localtime().tm_hour,
                "targets": {
                    "fan_on_temp": fan_on,
                    "fan_off_temp": fan_off,
                    "heater_on_temp": heater_on,
                    "heater_off_temp": heater_off,
                    "target_temp": target_temp,
                    "batch_age_day": batch_age_day
                },
                "intrusion_active": False, # Placeholder
                "preheat_recommended": False
            }
            
            # Submete o cenario para a AI (FSM)
            result = fsm.process_context(context)

            # Proteção contra Amônia (Regra Zootécnica de Qualidade do Ar)
            if sensor_state["ammonia_ppm"] > 20.0 and not result["ventilacao"]:
                result["ventilacao"] = True
                result["changes"].append("ventilacao ligada por amonia elevada")

            # Proteção contra Estresse Térmico Combinado (Regra Zootécnica Temp + UR > 115)
            curr_temp = sensor_state["temperature_c"]
            curr_hum = sensor_state["humidity_pct"]
            if (curr_temp + curr_hum) > 115.0 and curr_temp > 24.0 and not result["ventilacao"]:
                result["ventilacao"] = True
                result["changes"].append("ventilacao ligada por estresse termico calor+umidade")
            
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
