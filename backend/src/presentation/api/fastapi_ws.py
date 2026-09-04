import socketio
import logging
import jwt
import os

from src.security.headers import ALLOWED_ORIGINS
from src.security.fastapi_auth import SUPABASE_JWT_SECRET, _get_supabase_public_key, get_current_user

logger = logging.getLogger(__name__)

# O mesmo segredo JWT da autenticacao FastAPI


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
        # Valida token e verifica banco de dados (status/role) via auth global
        user_context = await get_current_user(token)
        user_id = user_context.user_id
        tenant_id = user_context.tenant_id
        
        async with sio.session(sid) as session:
            session['user_id'] = user_id
            session['tenant_id'] = tenant_id
            session['role'] = user_context.role

        # Isolamento Multi-Tenant: adiciona o cliente na sala do seu respectivo tenant
        await sio.enter_room(sid, f"tenant_{tenant_id}")
        if user_context.role in ("superadmin", "admin"):
            await sio.enter_room(sid, "elevated_admins")
            
        logger.info(f"Cliente SocketIO conectado - SID: {sid} (User: {user_id}, Tenant: {tenant_id})")
        return True
    except Exception as e:
        logger.error(f"Conexao SocketIO rejeitada (Token invalido) - SID: {sid} -  {str(e)}")
        return False

@sio.event
async def disconnect(sid):
    logger.info(f"Cliente SocketIO desconectado - SID: {sid}")

# Funcao helper para emitir alertas com suporte a isolamento por tenant
async def emit_new_alert(event_payload, tenant_id=None):
    """
    Emite alerta em tempo real para os clientes conectados.
    Se tenant_id for informado, isola a emissão na sala do respectivo tenant.
    """
    if tenant_id is not None:
        await sio.emit("new_alert", event_payload, room=f"tenant_{tenant_id}")
        await sio.emit("new_alert", event_payload, room="elevated_admins")
    else:
        await sio.emit("new_alert", event_payload)
