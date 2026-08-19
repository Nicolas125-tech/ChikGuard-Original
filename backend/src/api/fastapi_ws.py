import socketio
import logging
import jwt
import os

from src.security.headers import ALLOWED_ORIGINS
from src.security.fastapi_auth import _get_supabase_public_key

logger = logging.getLogger(__name__)

# O mesmo segredo JWT da autenticacao FastAPI
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")

# Usamos AsyncServer com allowed_origins restritas para seguranca
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=ALLOWED_ORIGINS)

# Esta app ASGI envolvera o FastAPI no main.py
socket_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ, auth):
    """
    Autentica a conexao do SocketIO verificando o token JWT.
    O frontend deve enviar: socket.io-client({ auth: { token: '...' } })
    """
    token = None
    if auth and "token" in auth:
        token = auth["token"]
    
    if not token:
        logger.warning(f"Conexao SocketIO rejeitada (Sem token) - SID: {sid}")
        return False # Rejeita

    try:
        # Valida token simples com suporte a ES256
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        decoded = None

        if alg == "ES256":
            public_key = _get_supabase_public_key(token)
            if public_key:
                decoded = jwt.decode(
                    token, public_key, algorithms=["ES256"], audience="authenticated"
                )

        if decoded is None:
            jwt_secret = os.environ.get("SUPABASE_JWT_SECRET") or SUPABASE_JWT_SECRET
            if jwt_secret:
                decoded = jwt.decode(
                    token, jwt_secret, algorithms=["HS256"], audience="authenticated"
                )

        if decoded is None:
            raise Exception("Token inválido")

        user_id = decoded.get("sub")
        
        async with sio.session(sid) as session:
            session['user_id'] = user_id
            
        logger.info(f"Cliente SocketIO conectado - SID: {sid} (User: {user_id})")
        return True
    except Exception as e:
        logger.error(f"Conexao SocketIO rejeitada (Token invalido) - SID: {sid} -  {str(e)}")
        return False

@sio.event
async def disconnect(sid):
    logger.info(f"Cliente SocketIO desconectado - SID: {sid}")

# Funcao helper para emitir alertas (sera chamada pelo backend core/FSM)
async def emit_new_alert(event_payload):
    """
    Substitui o `socketio.emit("new_alert", ...)` antigo do Flask.
    """
    await sio.emit("new_alert", event_payload)
