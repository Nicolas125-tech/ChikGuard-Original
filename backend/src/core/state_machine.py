class BusinessStateMachine:
    def __init__(self):
        self.state = 'NORMAL'

    def process_context(self, context):
        temp_atual = context.get('temp_atual', 25.0)
        targets = context.get('targets', {})
        hour = context.get('hour', 12)
        intrusion_active = context.get('intrusion_active', False)
        preheat_recommended = context.get('preheat_recommended', False)
        ventilacao_on = context.get('ventilacao_on', False)
        aquecedor_on = context.get('aquecedor_on', False)

        fan_on_temp = targets.get('fan_on_temp', 32.0)
        fan_off_temp = targets.get('fan_off_temp', 31.0)
        heater_on_temp = targets.get('heater_on_temp', 24.0)
        heater_off_temp = targets.get('heater_off_temp', 25.0)
        target_temp = targets.get('target_temp', 28.0)
        batch_age_day = targets.get('batch_age_day', 21)

        # Determine state
        if intrusion_active:
            self.state = 'ALARME_INTRUSO_ATIVO'
        elif batch_age_day <= 7:
            self.state = 'LOTE_DIA_1_AQUECIMENTO_CRITICO'
        elif preheat_recommended and (hour >= 18 or hour <= 6):
            self.state = 'NOITE_POUPANCA_ENERGIA_PREHEAT'
        elif 18 <= hour <= 23 or 0 <= hour <= 6:
            self.state = 'NOITE_POUPANCA_ENERGIA'
        else:
            self.state = 'NORMAL'

        ventilacao = ventilacao_on
        aquecedor = aquecedor_on

        # Output logic
        if self.state == 'ALARME_INTRUSO_ATIVO':
            if temp_atual >= fan_on_temp:
                ventilacao = True
            if temp_atual <= heater_on_temp:
                aquecedor = True
        elif self.state == 'LOTE_DIA_1_AQUECIMENTO_CRITICO':
            if temp_atual <= target_temp:
                aquecedor = True
            elif temp_atual >= heater_off_temp:
                aquecedor = False

            if temp_atual <= fan_off_temp:
                ventilacao = False
            elif temp_atual >= fan_on_temp:
                ventilacao = True
        elif self.state == 'NOITE_POUPANCA_ENERGIA_PREHEAT':
            aquecedor = True
            if temp_atual <= fan_off_temp:
                ventilacao = False
        elif self.state == 'NOITE_POUPANCA_ENERGIA':
            if temp_atual <= heater_on_temp:
                aquecedor = True
            elif temp_atual >= heater_off_temp:
                aquecedor = False

            if temp_atual <= fan_off_temp:
                ventilacao = False
            elif temp_atual >= fan_on_temp:
                ventilacao = True
        else:  # NORMAL
            if temp_atual >= fan_on_temp:
                ventilacao = True
            elif temp_atual <= fan_off_temp and temp_atual < fan_on_temp:
                ventilacao = False

            if temp_atual <= heater_on_temp:
                aquecedor = True
            elif temp_atual >= heater_off_temp:
                aquecedor = False

        changes = []
        if ventilacao and not ventilacao_on:
            changes.append("ventilacao ligada")
        elif not ventilacao and ventilacao_on:
            changes.append("ventilacao desligada")

        if aquecedor and not aquecedor_on:
            changes.append("aquecedor ligado")
        elif not aquecedor and aquecedor_on:
            changes.append("aquecedor desligado")

        return {
            'ventilacao': ventilacao,
            'aquecedor': aquecedor,
            'changes': changes,
            'state': self.state
        }
