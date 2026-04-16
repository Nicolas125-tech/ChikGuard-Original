#!/bin/bash
# Script de Monitoramento e Auto-Recuperação do ChikGuard (Edge)

SERVICE_NAME="chikguard.service"
WEBHOOK_URL="http://localhost:5000/api/system-info" # We use an internal endpoint just to check health for now

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_service() {
    systemctl is-active --quiet $SERVICE_NAME
    return $?
}

check_health() {
    # Test se a API local está respondendo
    curl -sSf $WEBHOOK_URL > /dev/null
    return $?
}

notify_mobile() {
    # Em um cenário real, isso faria uma chamada POST para um endpoint
    # do backend (que deve estar de volta no ar) para enviar um alerta push.
    # Ex: curl -X POST -H "Content-Type: application/json" -d '{"message": "Sistema Edge recuperado apos falha"}' http://localhost:5000/api/alerts/notify
    log "Enviando notificacao para a aplicacao movel sobre o reinicio do sistema."
}

log "Iniciando monitoramento do servico $SERVICE_NAME..."

while true; do
    if ! check_service; then
        log "ALERTA: Servico $SERVICE_NAME inativo. Tentando reiniciar..."
        systemctl restart $SERVICE_NAME
        sleep 30 # Aguardar startup

        if check_service && check_health; then
            log "SUCESSO: Sistema reiniciado com sucesso."
            notify_mobile
        else
            log "ERRO FATAL: Falha ao reiniciar o sistema."
        fi
    else
        if ! check_health; then
             log "ALERTA: O serviço está ativo, mas a API não responde. Reiniciando contêineres..."
             systemctl restart $SERVICE_NAME
             sleep 30

             if check_health; then
                 log "SUCESSO: API recuperada apos reinicio."
                 notify_mobile
             else
                 log "ERRO FATAL: API nao responde mesmo apos reinicio."
             fi
        fi
    fi
    sleep 60
done
