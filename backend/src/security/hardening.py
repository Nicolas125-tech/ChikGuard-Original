import logging
import re
import time

from flask import jsonify, request

logger = logging.getLogger(__name__)

# Configurações de Hardening e Constantes de Segurança
BLOCK_DURATION_SEC = 86400  # Bloqueio de 24 horas para IPs maliciosos
TARPIT_DELAY_SEC = 10  # Tempo de retenção para esgotar recursos de bots
RATE_LIMIT_MAX = 60  # Limite máximo de requisições por minuto
RATE_LIMIT_WINDOW = 60  # Janela temporal em segundos

# Dicionários em memória para controle de ameaças
BLACKLISTED_IPS = {}  # IP -> epoch_bloqueado_ate
IP_REQUESTS = {}  # IP -> [lista de epochs de acesso]

# Assinaturas de rotas sensíveis visadas por ferramentas de scan (scanners honeypots)
HONEYPOT_PATTERNS = [
    r"^/wp-",
    r"^/phpmyadmin",
    r"^/admin\.php",
    r"^/shell",
    r"^/webshell",
    r"^/setup\.cgi",
    r"^/xmlrpc",
    r"^/config",
    r"\.git",
    r"\.env",
    r"^/etc/passwd",
    r"^/axis2",
    r"^/actuator",
    r"^/api/v1/debug",
]
HONEYPOT_COMPILED = [re.compile(p, re.IGNORECASE) for p in HONEYPOT_PATTERNS]

# Padrões comuns de SQL Injection (SQLi) e Cross-Site Scripting (XSS)
SQLI_PATTERNS = [
    r"'\s*or\s*'\d+'\s*=\s*'\d+",
    r"union\s+select",
    r"--",
    r"/\*.*?\*/",
    r"select\s+.*\s+from",
    r"drop\s+table",
    r"insert\s+into",
]
SQLI_COMPILED = [re.compile(p, re.IGNORECASE) for p in SQLI_PATTERNS]

XSS_PATTERNS = [
    r"<script.*?>",
    r"javascript:",
    r"onerror\s*=",
    r"onload\s*=",
    r"<iframe.*?>",
    r"alert\(",
]
XSS_COMPILED = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]


# ── Funções Auxiliares de Gerenciamento de Estado ──


def is_blacklisted(ip):
    """Determina se um IP está atualmente bloqueado no sistema."""
    blocked_until = BLACKLISTED_IPS.get(ip, 0)
    if blocked_until > time.time():
        return True

    # Remove IP da blacklist se o prazo do bloqueio expirou
    if ip in BLACKLISTED_IPS:
        del BLACKLISTED_IPS[ip]
    return False


def blacklist_ip(ip, reason):
    """Registra um IP na lista negra do sistema pelo tempo regulamentar."""
    BLACKLISTED_IPS[ip] = time.time() + BLOCK_DURATION_SEC
    logger.error(f"[SECURITY-ALERT] IP {ip} adicionado à lista negra. Motivo: {reason}")


def check_rate_limiting(ip):
    """Controla o volume de requisições de um IP dentro da janela configurada."""
    now = time.time()
    access_history = IP_REQUESTS.get(ip, [])

    # Filtra requisições que saíram da janela de observação
    recent_accesses = [t for t in access_history if now - t < RATE_LIMIT_WINDOW]
    recent_accesses.append(now)
    IP_REQUESTS[ip] = recent_accesses

    if len(recent_accesses) > RATE_LIMIT_MAX:
        blacklist_ip(ip, f"Limite de requisições violado ({len(recent_accesses)}/min).")
        return False
    return True


def check_input_payload(payload):
    """Escaneia um conteúdo textual para identificar assinaturas de SQLi ou XSS."""
    if not payload:
        return True

    for pattern in SQLI_COMPILED:
        if pattern.search(payload):
            return False

    for pattern in XSS_COMPILED:
        if pattern.search(payload):
            return False

    return True


# ── Funções de Validação e Higienização (Clean Code - Single Responsibility) ──


def enforce_tarpit(delay_sec=TARPIT_DELAY_SEC):
    """Executa um atraso na conexão para exaustão de recursos do scanner."""
    time.sleep(delay_sec)


def validate_blacklisted_ip(ip):
    """Impõe restrições se o IP do cliente estiver na lista negra."""
    if is_blacklisted(ip):
        enforce_tarpit()
        return jsonify(
            {"error": "Acesso negado por histórico de ameaça", "code": "IP_BLACKLISTED"}
        ), 403
    return None


def validate_honeypots(ip, path):
    """Bloqueia e penaliza IPs tentando varrer rotas suspeitas."""
    for pattern in HONEYPOT_COMPILED:
        if pattern.search(path):
            blacklist_ip(ip, f"Tentou varrer a rota honeypot: {path}")
            enforce_tarpit()
            return jsonify({"error": "Acesso não autorizado", "code": "HONEYPOT_TRIGGERED"}), 403
    return None


def validate_rate_limiting(ip):
    """Garante que a cota de acessos por minuto do IP não seja violada."""
    if not check_rate_limiting(ip):
        enforce_tarpit()
        return jsonify(
            {"error": "Taxa de requisições excedida", "code": "RATE_LIMIT_EXCEEDED"}
        ), 429
    return None


def sanitize_request_data(ip):
    """Inspeciona query strings e corpo JSON para banir injeções maliciosas."""
    # 1. Validação de Query Params
    for key, val in request.args.items():
        if not check_input_payload(val):
            blacklist_ip(ip, f"Código suspeito no query param '{key}'={val}")
            return jsonify(
                {"error": "Payload inválido ou suspeito detectado", "code": "SUSPICIOUS_PAYLOAD"}
            ), 400

    # 2. Validação do JSON Body
    if request.is_json:
        try:
            raw_json = request.get_data(as_text=True)
            if not check_input_payload(raw_json):
                blacklist_ip(ip, "Código suspeito injetado no payload JSON")
                return jsonify(
                    {
                        "error": "Payload inválido ou suspeito detectado",
                        "code": "SUSPICIOUS_PAYLOAD",
                    }
                ), 400
        except Exception:
            pass

    return None


# ── Inicializador Principal ──


def setup_hardening(app):
    """
    Adiciona ganchos de segurança no fluxo HTTP do Flask
    para interceptação e descaracterização do servidor.
    """

    @app.before_request
    def block_malicious_requests():
        client_ip = request.remote_addr or "127.0.0.1"

        # Validação declarativa em cadeia de responsabilidade
        rejection = (
            validate_blacklisted_ip(client_ip)
            or validate_honeypots(client_ip, request.path)
            or validate_rate_limiting(client_ip)
            or sanitize_request_data(client_ip)
        )
        return rejection

    @app.after_request
    def mask_technology_fingerprints(response):
        """Altera os cabeçalhos de resposta para impedir banner grabbing e fortalece a segurança."""
        response.headers["Server"] = "Secure-Gateway"
        response.headers.pop("X-Powered-By", None)
        # Security Headers Improvement
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

    logger.info("Filtros ativos do Hardening de Segurança inicializados com sucesso.")
