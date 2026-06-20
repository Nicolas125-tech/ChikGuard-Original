import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import load_settings
from src.core.logger import configure_logging
from src.core.fsm_task import fsm_loop
from src.core.mqtt_bridge import start_mqtt_bridge
import asyncio

# Configuracoes e Logger base
SETTINGS = load_settings()
LOGGER = configure_logging(SETTINGS.log_level)

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    # Setup de inicializacao do backend (conexao com DB, modelos AI, etc)
    LOGGER.info("Iniciando o servidor FastAPI - ChikGuard")
    
    # Inicia a Ponte IoT (MQTT)
    mqtt_client = await start_mqtt_bridge()
    
    # Inicia o FSM em background
    fsm_task = asyncio.create_task(fsm_loop())
    
    yield
    
    # Cleanup na finalizacao
    fsm_task.cancel()
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        
    LOGGER.info("Encerrando o servidor FastAPI - ChikGuard")

from src.api.fastapi_health import router as health_router
from src.api.fastapi_sensors import router as sensors_router
from src.api.fastapi_birds import router_birds, router_weight
from src.api.fastapi_webrtc import router as webrtc_router
from src.api.fastapi_iot import router as iot_router
from src.api.fastapi_ws import socket_app
from src.security.headers import ALLOWED_ORIGINS

fastapi_app = FastAPI(
    title="ChikGuard API",
    description="Backend refatorado em FastAPI para monitoramento avicola inteligente.",
    version="2.0.0",
    lifespan=lifespan,
)

fastapi_app.include_router(health_router)
fastapi_app.include_router(sensors_router)
fastapi_app.include_router(router_birds)
fastapi_app.include_router(router_weight)
fastapi_app.include_router(webrtc_router)
fastapi_app.include_router(iot_router)

# CORS middleware
# Ajustando os ALLOWED_ORIGINS buscando de src.security.headers para seguranca
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@fastapi_app.get("/")
async def root():
    return {
        "status": "online",
        "service": "ChikGuard FastAPI Edge Node",
        "version": "2.0.0"
    }

@fastapi_app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    LOGGER.error(f"Erro nao tratado na rota {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Ocorreu um erro interno no servidor."},
    )

# O ASGI App final que uvicorn vai rodar e a composicao do SocketIO + FastAPI
socket_app.other_asgi_app = fastapi_app
app = socket_app
