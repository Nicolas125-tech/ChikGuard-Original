import os
import logging
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

def get_device_id_or_ip():
    """
    Estrategia de Rate Limiting (Zero Trust):
    Se a requisicao vier do Edge (Mini PC via API ou Tunnel), tenta obter
    o Device ID autenticado. Se for login publico, usa o IP de origem.
    """
    device_id = request.headers.get("X-Device-ID")
    if device_id:
        return f"device:{device_id}"

    # Se o IP real vier de um Proxy Reverso (ex: Cloudflare / Nginx)
    real_ip = request.headers.get("X-Forwarded-For")
    if real_ip:
        return real_ip.split(',')[0].strip()

    return get_remote_address()

# Inicializacao do Flask-Limiter usando Redis (ou Memory fallback em Dev)
redis_url = os.environ.get("REDIS_URL", "memory://")
logger.info(f"Inicializando Flask-Limiter com backend: {redis_url}")

limiter = Limiter(
    key_func=get_device_id_or_ip,
    storage_uri=redis_url,
    # Limites padrao globais para a API (Previne DDoS basico e raspagem de dados)
    default_limits=["1000 per day", "200 per hour"],
    strategy="fixed-window",
)

def setup_rate_limiting(app):
    """
    Configura e acopla o limiter ao Flask App.
    """
    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        """
        Garante que violacoes de limite (Forca Bruta)
        sejam logadas e devolvam um JSON estruturado.
        """
        logger.warning(f"Rate limit excedido por: {get_device_id_or_ip()} - Rota: {request.path}")
        return jsonify(
            error="Too Many Requests",
            message="Limite de requisicoes excedido. Aguarde antes de tentar novamente.",
            description=str(e.description)
        ), 429

# Decorators especificos para proteger rotas criticas
# Exemplo de uso nas rotas (no Blueprint/View):
# @app.route('/api/auth/login', methods=['POST'])
# @limiter.limit("5 per minute")  # Previne forca bruta no login
# def login(): ...
#
# @app.route('/api/telemetry/sync', methods=['POST'])
# @limiter.limit("60 per minute") # Previne inundacao de telemetria do Edge
# def sync_telemetry(): ...
