import logging
import os

from flask import jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)


def get_device_id_or_ip():
    """
    Estrategia de Rate Limiting:
    Usa o IP de origem resolvido com seguranca (atraves do ProxyFix em app.py).
    Ignorar X-Forwarded-For manualmente ou cabecalhos como X-Device-ID para
    evitar spoofing e bypass de Rate Limiting.
    """
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
            description=str(e.description),
        ), 429
