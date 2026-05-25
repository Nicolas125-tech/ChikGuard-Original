from src.core.state_machine import BusinessStateMachine

def test_dia_1_aquecimento_critico():
    fsm = BusinessStateMachine()
    targets = {
        'fan_on_temp': 34.0,
        'fan_off_temp': 33.0,
        'heater_on_temp': 31.5,
        'heater_off_temp': 32.2,
        'target_temp': 32.0,
        'batch_age_day': 1
    }

    # If temp is slightly below target_temp, it forces heater on to maintain high temps.
    context = {
        'temp_atual': 31.8,
        'targets': targets,
        'hour': 12,
        'intrusion_active': False,
        'preheat_recommended': False,
        'ventilacao_on': False,
        'aquecedor_on': False
    }

    result = fsm.process_context(context)
    assert result['state'] == 'LOTE_DIA_1_AQUECIMENTO_CRITICO'
    assert result['aquecedor'] is True
    assert result['ventilacao'] is False


def test_intrusao_ativo():
    fsm = BusinessStateMachine()
    targets = {
        'fan_on_temp': 32.0,
        'fan_off_temp': 31.0,
        'heater_on_temp': 24.0,
        'heater_off_temp': 25.0,
        'target_temp': 28.0,
        'batch_age_day': 21
    }

    context = {
        'temp_atual': 26.0,
        'targets': targets,
        'hour': 2,
        'intrusion_active': True,
        'preheat_recommended': False,
        'ventilacao_on': False,
        'aquecedor_on': False
    }

    result = fsm.process_context(context)
    assert result['state'] == 'ALARME_INTRUSO_ATIVO'
    # Within safe margins, devices don't randomly toggle.
    assert result['ventilacao'] is False
    assert result['aquecedor'] is False


def test_preheat():
    fsm = BusinessStateMachine()
    targets = {
        'fan_on_temp': 32.0,
        'fan_off_temp': 31.0,
        'heater_on_temp': 24.0,
        'heater_off_temp': 25.0,
        'target_temp': 28.0,
        'batch_age_day': 21
    }

    # Between 18 and 6, when a cold front is recommended
    context = {
        'temp_atual': 28.0, # Normal temp
        'targets': targets,
        'hour': 19,
        'intrusion_active': False,
        'preheat_recommended': True,
        'ventilacao_on': False,
        'aquecedor_on': False
    }

    result = fsm.process_context(context)
    assert result['state'] == 'NOITE_POUPANCA_ENERGIA_PREHEAT'
    assert result['aquecedor'] is True # Forced ON despite temp not reaching heater_on_temp
    assert result['ventilacao'] is False


def test_normal():
    fsm = BusinessStateMachine()
    targets = {
        'fan_on_temp': 32.0,
        'fan_off_temp': 31.0,
        'heater_on_temp': 24.0,
        'heater_off_temp': 25.0,
        'target_temp': 28.0,
        'batch_age_day': 21
    }

    context = {
        'temp_atual': 27.0,
        'targets': targets,
        'hour': 14,
        'intrusion_active': False,
        'preheat_recommended': False,
        'ventilacao_on': False,
        'aquecedor_on': False
    }

    result = fsm.process_context(context)
    assert result['state'] == 'NORMAL'
    assert result['ventilacao'] is False
    assert result['aquecedor'] is False
    assert len(result['changes']) == 0
