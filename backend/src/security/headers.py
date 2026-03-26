import os
import logging
from flask import request
from flask_cors import CORS

logger = logging.getLogger(__name__)

# Definir os dominios confiaveis autorizados a acessar a API.
# Este array deve ser mapeado a partir de variaveis de ambiente em Producao.
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,https://app.chikguard.com"
).split(",")

def setup_cors(app):
    """
    Configura o CORS estrito apenas para dominios listados.
    Isso impede que paginas web maliciosas (CSRF / XSS) facam
    chamadas Ajax nao autorizadas para a nossa API.
    """
    logger.info(f"CORS restrito a: {ALLOWED_ORIGINS}")

    CORS(
        app,
        resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
        # Garante que credenciais (Cookies de sessao / Cookies Secure) sejam enviados
        # apenas se as origens coincidirem e forem HTTPS.
        supports_credentials=True,
        # Metodos e headers aceites. Impede "preflight hijacking".
        allow_headers=["Content-Type", "Authorization", "X-Device-ID"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

def setup_security_headers(app):
    """
    Injeta headers rigorosos de Content Security Policy (CSP)
    e demais medidas preventivas (HSTS, Anti-Sniffing) em
    todas as respostas HTTP do backend Flask.
    """
    @app.after_request
    def set_secure_headers(response):
        # Evita enquadramento da aplicacao em iframes (Clickjacking)
        response.headers['X-Frame-Options'] = 'DENY'

        # Previne MIME-type sniffing (forca o browser a respeitar o content-type)
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Ativa o filtro XSS basico em browsers mais antigos
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Enforca HTTPS em browsers (HSTS). Impede downgrades para HTTP plano.
        # Valido por 1 ano. Inclui subdominios.
        if os.environ.get("FLASK_ENV") != "development":
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Content Security Policy (CSP) rigoroso para respostas de API.
        # Restringe a origem de scripts, recursos embutidos (iframes) e object-tags,
        # permitindo que a API retorne primariamente JSON.
        csp_rules = [
            "default-src 'none'",                # Omissao padrao: bloqeia tudo.
            "frame-ancestors 'none'",           # Reforca o anti-clickjacking.
            "base-uri 'none'",                  # Evita injeccao de tag <base>.
            "form-action 'none'",               # Nao permite submissao de formularios HTLM.
            "script-src 'none'",                # Nenhum javascript sera injetado ou rodado a partir da reposta da API
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_rules)

        # Header customizado para identificar a versao/instancia e auditoria
        response.headers['X-Edge-Device'] = os.environ.get("DEVICE_ID", "ChikGuard-Cloud-API")

        return response
