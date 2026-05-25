from typing import Dict, Any, List, Tuple

class BusinessStateMachine:
    """
    Máquina de Estados Climática do ChikGuard.
    Analisa a temperatura atual, idade do lote e alarmes físicos para determinar o estado e
    acionar os atuadores (aquecedor/ventilador), aplicando limites rígidos de segurança.
    """
    
    # Limites Físicos Rígidos de Segurança (Hard-Limits Watchdog)
    MAX_SAFE_FAN_ON = 34.0
    MIN_SAFE_FAN_ON = 26.0
    MAX_SAFE_HEATER_ON = 28.0
    MIN_SAFE_HEATER_ON = 18.0

    def __init__(self):
        self.state = 'NORMAL'

    def _clamp_safety_limits(self, targets: Dict[str, float]) -> Tuple[float, float, float, float]:
        """Aplica limites de segurança (Watchdog) sobre as metas recomendadas pelos agentes."""
        raw_fan_on = targets.get('fan_on_temp', 32.0)
        fan_on = min(max(raw_fan_on, self.MIN_SAFE_FAN_ON), self.MAX_SAFE_FAN_ON)

        raw_fan_off = targets.get('fan_off_temp', 31.0)
        # Histerese mínima de 0.5°C para o ventilador
        fan_off = min(raw_fan_off, fan_on - 0.5)

        raw_heater_on = targets.get('heater_on_temp', 24.0)
        heater_on = min(max(raw_heater_on, self.MIN_SAFE_HEATER_ON), self.MAX_SAFE_HEATER_ON)

        raw_heater_off = targets.get('heater_off_temp', 25.0)
        # Histerese mínima de 0.5°C para o aquecedor
        heater_off = max(raw_heater_off, heater_on + 0.5)

        return fan_on, fan_off, heater_on, heater_off

    def _determine_state(self, intrusion_active: bool, batch_age_day: int, preheat_recommended: bool, hour: int) -> str:
        """Infere o estado operacional correto com base no contexto do aviário."""
        if intrusion_active:
            return 'ALARME_INTRUSO_ATIVO'
        if batch_age_day <= 7:
            return 'LOTE_DIA_1_AQUECIMENTO_CRITICO'
        
        is_night = 18 <= hour <= 23 or 0 <= hour <= 6
        if preheat_recommended and is_night:
            return 'NOITE_POUPANCA_ENERGIA_PREHEAT'
        if is_night:
            return 'NOITE_POUPANCA_ENERGIA'
            
        return 'NORMAL'

    # ── Regras de Controle Térmico por Estado (SRP) ──

    def _control_alarm_intruso(self, temp: float, fan_on: float, heater_on: float, vent: bool, heat: bool) -> Tuple[bool, bool]:
        """Atua sob alarme de intruso ativo."""
        return (temp >= fan_on, temp <= heater_on)

    def _control_lote_critico(self, temp: float, fan_on: float, fan_off: float, heater_off: float, target_temp: float, vent: bool, heat: bool) -> Tuple[bool, bool]:
        """Atua sob aquecimento crítico para pintinhos na primeira semana."""
        new_heat = heat
        new_vent = vent

        if temp <= target_temp:
            new_heat = True
        elif temp >= heater_off:
            new_heat = False

        if temp <= fan_off:
            new_vent = False
        elif temp >= fan_on:
            new_vent = True

        return new_vent, new_heat

    def _control_noite_preheat(self, temp: float, fan_off: float, vent: bool, heat: bool) -> Tuple[bool, bool]:
        """Atua sob modo pré-aquecimento preventivo noturno."""
        new_vent = False if temp <= fan_off else vent
        return new_vent, True

    def _control_noite_poupanca(self, temp: float, fan_on: float, fan_off: float, heater_on: float, heater_off: float, vent: bool, heat: bool) -> Tuple[bool, bool]:
        """Atua sob modo de poupança de energia noturno tradicional."""
        new_heat = heat
        new_vent = vent

        if temp <= heater_on:
            new_heat = True
        elif temp >= heater_off:
            new_heat = False

        if temp <= fan_off:
            new_vent = False
        elif temp >= fan_on:
            new_vent = True

        return new_vent, new_heat

    def _control_normal(self, temp: float, fan_on: float, fan_off: float, heater_on: float, heater_off: float, vent: bool, heat: bool) -> Tuple[bool, bool]:
        """Atua sob condições de operação diurna normal."""
        new_vent = vent
        new_heat = heat

        if temp >= fan_on:
            new_vent = True
        elif temp <= fan_off:
            new_vent = False

        if temp <= heater_on:
            new_heat = True
        elif temp >= heater_off:
            new_heat = False

        return new_vent, new_heat

    def _detect_changes(self, vent: bool, vent_prev: bool, heat: bool, heat_prev: bool) -> List[str]:
        """Gera logs de auditoria textual para mudanças de estado físico dos atuadores."""
        changes = []
        if vent and not vent_prev:
            changes.append("ventilacao ligada")
        elif not vent and vent_prev:
            changes.append("ventilacao desligada")

        if heat and not heat_prev:
            changes.append("aquecedor ligado")
        elif not heat and heat_prev:
            changes.append("aquecedor desligado")
        return changes

    def process_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Processa a leitura térmica atual e comanda a atuação do aviário."""
        temp_atual = context.get('temp_atual', 25.0)
        targets = context.get('targets', {})
        hour = context.get('hour', 12)
        
        # Leitura inicial dos atuadores
        ventilacao_on = context.get('ventilacao_on', False)
        aquecedor_on = context.get('aquecedor_on', False)

        # 1. Ajuste e Watchdog de Segurança das Metas
        fan_on, fan_off, heater_on, heater_off = self._clamp_safety_limits(targets)

        # 2. Resolução do Estado Operacional
        self.state = self._determine_state(
            intrusion_active=context.get('intrusion_active', False),
            batch_age_day=targets.get('batch_age_day', 21),
            preheat_recommended=context.get('preheat_recommended', False),
            hour=hour
        )

        # 3. Execução das Regras de Atuação
        if self.state == 'ALARME_INTRUSO_ATIVO':
            vent, heat = self._control_alarm_intruso(temp_atual, fan_on, heater_on, ventilacao_on, aquecedor_on)
        elif self.state == 'LOTE_DIA_1_AQUECIMENTO_CRITICO':
            vent, heat = self._control_lote_critico(temp_atual, fan_on, fan_off, heater_off, targets.get('target_temp', 28.0), ventilacao_on, aquecedor_on)
        elif self.state == 'NOITE_POUPANCA_ENERGIA_PREHEAT':
            vent, heat = self._control_noite_preheat(temp_atual, fan_off, ventilacao_on, aquecedor_on)
        elif self.state == 'NOITE_POUPANCA_ENERGIA':
            vent, heat = self._control_noite_poupanca(temp_atual, fan_on, fan_off, heater_on, heater_off, ventilacao_on, aquecedor_on)
        else:
            vent, heat = self._control_normal(temp_atual, fan_on, fan_off, heater_on, heater_off, ventilacao_on, aquecedor_on)

        # 4. Auditoria de Alterações
        changes = self._detect_changes(vent, ventilacao_on, heat, aquecedor_on)

        return {
            'ventilacao': vent,
            'aquecedor': heat,
            'changes': changes,
            'state': self.state
        }
