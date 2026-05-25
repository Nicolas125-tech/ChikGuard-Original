import logging
import time
import re
from flask import request, jsonify, abort

logger = logging.getLogger(__name__)

# Configurações de Hardening
BLOCK_DURATION_SEC = 86400  # Bloqueio de 24 horas para atacantes identificados
TARPIT_DELAY_SEC = 10      # Atraso em segundos para esgotar recursos de scanners
RATE_LIMIT_MAX = 60        # Máximo de 60 requisições por minuto
RATE_LIMIT_WINDOW = 60     # Janela de tempo de 60 segundos

# Banco de dados em memória para segurança local
BLACKLISTED_IPS = {}       # IP -> epoch_bloqueado_ate
IP_REQUESTS = {}           # IP -> [lista de epochs dos acessos]

# Assinaturas de Honeypots de caminhos visados por hackers (Kali Linux, Dirb, Nmap)
HONEYPOT_PATTERNS = [
    r"^/wp-", r"^/phpmyadmin", r"^/admin\.php", r"^/shell", r"^/webshell", 
    r"^/setup\.cgi", r"^/xmlrpc", r"^/config", r"\.git", r"\.env", 
    r"^/etc/passwd", r"^/axis2", r"^/actuator", r"^/api/v1/debug"
]
HONEYPOT_COMPILED = [re.compile(p, re.IGNORECASE) for p in HONEYPOT_PATTERNS]

# Padrões comuns de SQL Injection (SQLi) e XSS
SQLI_PATTERNS = [
    r"'\s*or\s*'\d+'\s*=\s*'\d+", r"union\s+select", r"--", r"/\*.*?\*/", 
    r"select\s+.*\s+from", r"drop\s+table", r"insert\s+into"
]
SQLI_COMPILED = [re.compile(p, re.IGNORECASE) for p in SQLI_PATTERNS]

XSS_PATTERNS = [
    r"<script.*?>", r"javascript:", r"onerror\s*=", r"onload\s*=", 
    r"<iframe.*?>", r"alert\("
]
XSS_COMPILED = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]


def is_blacklisted(ip):
    """Verifica se o IP está ativamente bloqueado."""
    blocked_until = BLACKLISTED_IPS.get(ip, 0)
    if blocked_until > time.time():
        return True
    elif ip in BLACKLISTED_IPS:
        # Período de bloqueio expirou
        del BLACKLISTED_IPS[ip]
    return False


def blacklist_ip(ip, reason):
    """Adiciona o IP à lista negra e loga a ameaça."""
    BLACKLISTED_IPS[ip] = time.time() + BLOCK_DURATION_SEC
    logger.error(f"[SECURITY-ALERT] IP {ip} bloqueado por 24h. Motivo: {reason}")


def check_rate_limiting(ip):
    """Verifica e aplica limitação de taxa (Rate Limiting) simples por IP."""
    now = time.time()
    times = IP_REQUESTS.get(ip, [])
    
    # Filtra apenas requisições dentro da janela de tempo recente
    times = [t for t in times if now - t < RATE_LIMIT_WINDOW]
    times.append(now)
    IP_REQUESTS[ip] = times

    if len(times) > RATE_LIMIT_MAX:
        blacklist_ip(ip, f"Excesso de requisições ({len(times)}/min). Rate limit violado.")
        return False
    return True


def check_input_payload(data_str):
    """Varre strings de requisição procurando SQLi ou XSS."""
    if not data_str:
        return True
    
    for pattern in SQLI_COMPILED:
        if pattern.search(data_str):
            return False
            
    for pattern in XSS_COMPILED:
        if pattern.search(data_str):
            return False
            
    return True


def setup_hardening(app):
    """
    Configura proteções ativas contra varreduras do Kali Linux,
    Nmap e ataques direcionados na camada HTTP do Flask.
    """
    
    @app.before_request
    def block_malicious_requests():
        client_ip = request.remote_addr or "127.0.0.1"

        # 1. Bloqueio e Tarpit para IPs na Blacklist
        if is_blacklisted(client_ip):
            # Atraso deliberado para consumir recursos do scanner (Tarpitting)
            time.sleep(TARPIT_DELAY_SEC)
            return jsonify({
                "error": "Acesso permanentemente bloqueado por comportamento hostil", 
                "code": "IP_BLACKLISTED"
            }), 403

        # 2. Detecção de Honeypot / Scanner de Rotas
        path = request.path
        for pattern in HONEYPOT_COMPILED:
            if pattern.search(path):
                blacklist_ip(client_ip, f"Tentativa de acesso a rota protegida/honeypot: {path}")
                time.sleep(TARPIT_DELAY_SEC)
                return jsonify({"error": "Acesso não autorizado", "code": "HONEYPOT_TRIGGERED"}), 403

        # 3. Executa validação de Rate Limit
        if not check_rate_limiting(client_ip):
            time.sleep(TARPIT_DELAY_SEC)
            return jsonify({"error": "Taxa de requisições excedida", "code": "RATE_LIMIT_EXCEEDED"}), 429

        # 4. Higienização de Payload (Evita SQLi e XSS em Query Strings e JSON)
        # Verifica Query Parameters
        for key, val in request.args.items():
            if not check_input_payload(val):
                blacklist_ip(client_ip, f"Tentativa de Injeção (SQLi/XSS) detectada no parâmetro '{key}'={val}")
                return jsonify({"error": "Payload inválido ou suspeito detectado", "code": "SUSPICIOUS_PAYLOAD"}), 400

        # Verifica JSON Body
        if request.is_json:
            try:
                raw_json = request.get_data(as_text=True)
                if not check_input_payload(raw_json):
                    blacklist_ip(client_ip, "Tentativa de Injeção (SQLi/XSS) detectada no corpo JSON")
                    return jsonify({"error": "Payload inválido ou suspeito detectado", "code": "SUSPICIOUS_PAYLOAD"}), 400
            except Exception:
                pass

        return None

    @app.after_request
    def remove_server_fingerprints(response):
        """Remove ou altera cabeçalhos que revelam a pilha de tecnologia (Evita Banner Grabbing)."""
        response.headers['Server'] = 'Secure-Gateway'
        response.headers.pop('X-Powered-By', None)
        return response

    logger.info("Módulo de Hardening e Proteção Anti-Intrusão ativado.")
