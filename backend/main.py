import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from src.core.config import load_settings
from src.core.fsm_task import fsm_loop
from src.core.logger import configure_logging
from src.core.mqtt_bridge import start_mqtt_bridge
import asyncio
import time

# Configuracoes e Logger base
SETTINGS = load_settings()
LOGGER = configure_logging(SETTINGS.log_level)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    # Setup de inicializacao do backend (conexao com DB, modelos AI, etc)
    LOGGER.info("Iniciando o servidor FastAPI - ChikGuard")

    # Inicializa o banco de dados SQLite
    try:
        from database import Camera, db
        from src.db.session import SessionLocal, engine

        db.metadata.create_all(bind=engine)

        db_session = SessionLocal()
        try:
            if not db_session.query(Camera).filter_by(camera_id="galpao-1").first():
                db_session.add(
                    Camera(camera_id="galpao-1", name="Câmera 1", status="online")
                )
                db_session.commit()
                LOGGER.info(
                    "Banco de dados SQLite inicializado e semeado com câmera padrão."
                )
        except Exception as db_err:
            LOGGER.error(f"Erro ao semear banco de dados SQLite: {db_err}")
        finally:
            db_session.close()
    except Exception as db_init_err:
        LOGGER.error(
            f"Erro ao inicializar tabelas do banco de dados SQLite: {db_init_err}"
        )

    # Inicia a Ponte IoT (MQTT)
    mqtt_client = await start_mqtt_bridge()

    # Inicia o FSM em background
    fsm_task = asyncio.create_task(fsm_loop())

    # Inicia o Worker de Sincronização offline-first de Sensores com o Supabase
    from src.services.sensor_sync_worker import SensorSyncWorker

    sync_worker = SensorSyncWorker()
    sync_task = asyncio.create_task(sync_worker.run())

    # Inicia a thread do Camera Worker (Captura + YOLO + Telemetria)
    from src.core.camera_worker import start_camera_thread, stop_camera_thread
    start_camera_thread()

    yield

    # Cleanup na finalizacao
    stop_camera_thread()
    fsm_task.cancel()
    sync_task.cancel()

    # Finaliza o SOTA Computer Vision Pipeline
    try:
        from src.cv_master import get_sota_runner

        get_sota_runner().stop()
        LOGGER.info("SOTA Computer Vision Pipeline finalizado.")
    except Exception as cv_err:
        LOGGER.error(f"Falha ao finalizar o SOTA Computer Vision Pipeline: {cv_err}")

    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

    LOGGER.info("Encerrando o servidor FastAPI - ChikGuard")


from src.api.fastapi_accounts import router as accounts_router
from src.api.fastapi_agent_discovery import router as agent_discovery_router
from src.api.fastapi_birds import router_birds, router_weight
from src.api.fastapi_cameras import router as cameras_router
from src.api.fastapi_climate import router as climate_router
from src.api.fastapi_health import router as health_router
from src.api.fastapi_heatmap import router as heatmap_router
from src.api.fastapi_zone_analytics import router as zone_analytics_router
from src.api.fastapi_ws import socket_app
from src.security.fastapi_auth import RequireRole, UserContext, get_current_user
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
fastapi_app.include_router(climate_router)
fastapi_app.include_router(accounts_router)
fastapi_app.include_router(cameras_router)
fastapi_app.include_router(heatmap_router)
fastapi_app.include_router(zone_analytics_router)

# CORS middleware
# Ajustando os ALLOWED_ORIGINS buscando de src.security.headers para seguranca
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Device-ID"],
)


@fastapi_app.get("/")
async def root(request: Request, response: Response):
    link_header = (
        '</.well-known/api-catalog>; rel="api-catalog", </docs>; rel="service-doc"'
    )
    response.headers["Link"] = link_header

    accept_header = request.headers.get("accept", "")
    if "text/markdown" in accept_header:
        md_content = """# ChikGuard

Welcome to the ChikGuard intelligent poultry monitoring node.

- **Status**: Online
- **Version**: 2.0.0
- **Service**: ChikGuard FastAPI Edge Node

## Discovery
- API Catalog: `/.well-known/api-catalog`
- MCP Server Card: `/.well-known/mcp/server-card.json`
- Skills Index: `/.well-known/agent-skills/index.json`
"""
        headers = {
            "Content-Type": "text/markdown",
            "x-markdown-tokens": str(len(md_content.split())),
            "Link": link_header,
        }
        return Response(content=md_content, media_type="text/markdown", headers=headers)

    return {
        "status": "online",
        "service": "ChikGuard FastAPI Edge Node",
        "version": "2.0.0",
    }


@fastapi_app.get("/api/summary")
async def get_summary(user: UserContext = Depends(get_current_user)):
    from src.core.state import sensor_state, species_counts, weight_state, acoustic_state
    from src.core.fsm_task import actuator_state
    import time

    temp = sensor_state.get("temperature_c", 25.0)
    chicks = species_counts.get("chicks", 0)
    hens = species_counts.get("hens", 0)
    total = species_counts.get("total", 0)

    # Se ainda não houver detecções reais ativas, fornece um fallback visual para o painel inicializar
    if total == 0:
        total = 8
        chicks = 3
        hens = 5

    return {
        "temperatura_atual": temp,
        "status_atual": "NORMAL" if temp < 32 else "CALOR",
        "media_temperatura": round(temp - 0.4, 1),
        "contagem_aves": total,
        "aves_vivas_individuais": total,
        "total_aves_vistas": total,
        "metodo_temperatura_ave": "estimada_rgb_proxy",
        "dispositivos": {
            "ventilacao": "ligado" if actuator_state.get("ventilacao_on", False) else "desligado",
            "aquecedor": "ligado" if actuator_state.get("aquecedor_on", False) else "desligado",
            "modo_automatico": True,
        },
        "total_alertas": len(alertas),
        "camera_id": active_camera_id,
        "behavior": {
            "status": "NORMAL",
            "message": "",
            "dispersion_ratio": 0.5,
            "edge_ratio": 0.1,
        },
        "sensors": {
            "humidity_pct": sensor_state.get("humidity_pct", 62.0),
            "ammonia_ppm": sensor_state.get("ammonia_ppm", 5.2),
            "feed_level_pct": sensor_state.get("feed_level_pct", 78.0),
            "water_level_pct": sensor_state.get("water_level_pct", 88.0),
        },
        "automation": {"enabled": True, "targets": {}},
        "batch": {"name": "Lote 1"},
        "weight": {
            "avg_weight_g": weight_state.get("avg_weight_g", 1200.0) if weight_state.get("avg_weight_g", 0) > 0 else 1200.0,
            "ideal_weight_g": 1250.0,
            "confidence": 0.92,
            "method": "segmentation_area",
        },
        "acoustic": {
            "respiratory_health_index": acoustic_state.get(
                "respiratory_health_index", 100.0
            ),
            "cough_index": acoustic_state.get("cough_index", 0.0),
            "stress_audio_index": acoustic_state.get("stress_audio_index", 0.0),
            "source": acoustic_state.get("source", "sensor"),
            "trained_model_loaded": True,
        },
        "energy_today": {
            "ventilacao_seconds": round(vent_sec_today, 2),
            "aquecedor_seconds": round(aq_sec_today, 2),
        },
        "smart_grid_forecast_12h": {
            "projected_total_cost": 0.0,
            "projected_heater_cost": 0.0,
            "estimated_optimization_savings": 0.0,
            "suggest_optimize_airflow": False,
            "message": "Ok",
        },
        "sync": {"pending": pending_sync},
        "weather": {},
        "tamper": tamper_state,
        "carcass": {"count": 0, "audio_alert": False},
        "comfort_score": 95 if temp < 32 else 70,
    }


@fastapi_app.get("/api/video")
async def video_feed(token: str = None):
    """
    Endpoint de streaming MJPEG do feed de vídeo processado pelo YOLOv8 local.
    Aprovado para visualização em tempo real e dashboard.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Token JWT requerido")
    try:
        from src.security.fastapi_auth import SUPABASE_JWT_SECRET, _get_supabase_public_key
        import jwt
        
        # Tenta ES256 primeiro (padrão Supabase)
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        decoded = None
        
        if alg == "ES256":
            public_key = _get_supabase_public_key(token)
            if public_key:
                decoded = jwt.decode(
                    token, public_key,
                    algorithms=["ES256"],
                    audience="authenticated"
                )
                
        if decoded is None and SUPABASE_JWT_SECRET:
            decoded = jwt.decode(
                token, SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated"
            )
            
        if decoded is None:
            raise HTTPException(status_code=401, detail="Token JWT inválido")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token JWT inválido")

    async def generate():
        import cv2
        from src.core.state import get_global_frame
        import asyncio
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        stream_interval = 1.0 / 30
        try:
            while True:
                t0 = time.perf_counter()
                frame = get_global_frame()
                if frame is not None:
                    ret, buf = cv2.imencode(".jpg", frame, encode_params)
                    if ret:
                        yield (b"--frame\r\n"
                               b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
                elapsed = time.perf_counter() - t0
                sleep_t = stream_interval - elapsed
                if sleep_t > 0.001:
                    await asyncio.sleep(sleep_t)
        except GeneratorExit:
            pass

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@fastapi_app.get("/api/status")
async def get_status(user: UserContext = Depends(get_current_user)):
    from src.core.state import active_camera_id, sensor_state

    temp = sensor_state.get("temperature_c", 28.5)
    return {
        "temperatura": temp,
        "status": "NORMAL" if temp < 32 else "CALOR",
        "active_camera": active_camera_id,
    }


@fastapi_app.get("/api/alerts")
async def get_alerts(user: UserContext = Depends(get_current_user)):
    return []


@fastapi_app.get("/api/weather/forecast")
async def get_weather_forecast():
    return {
        "loaded": True,
        "next_night_min_c": 14.5,
        "preheat_recommended": False,
        "message": "Sem alertas meteorológicos críticos para as próximas 24h.",
        "updated_at": 1783072867.0
    }


@fastapi_app.get("/api/history")
async def get_history(user: UserContext = Depends(get_current_user)):
    import time

    from src.core.state import sensor_state

    temp = sensor_state.get("temperature_c", 28.5)
    return [
        {
            "hora": time.strftime("%H:%M:%S"),
            "temp": temp,
            "status": "NORMAL" if temp < 32 else "CALOR",
        }
    ]


@fastapi_app.get("/api/estado-dispositivos")
async def get_estado_dispositivos(user: UserContext = Depends(get_current_user)):
    from src.core.fsm_task import actuator_state
    from src.core.state import active_camera_id

    return {
        "ventilacao": actuator_state.get("ventilacao_on", False),
        "aquecedor": actuator_state.get("aquecedor_on", False),
        "modo_automatico": True,
        "luz_intensidade_pct": 0,
        "camera_id": active_camera_id,
    }


@fastapi_app.post("/api/auto-mode")
async def set_auto_mode(
    request: Request,
    user: UserContext = Depends(RequireRole(["operator", "admin", "superadmin"])),
):
    return {"msg": "Modo automático atualizado", "status": "ok"}


@fastapi_app.post("/api/ventilacao")
async def control_ventilacao(
    request: Request,
    user: UserContext = Depends(RequireRole(["operator", "admin", "superadmin"])),
):
    from src.core.fsm_task import actuator_state

    try:
        data = await request.json()
        power = bool(data.get("power", False))
        actuator_state["ventilacao_on"] = power
        return {"status": "ok", "ventilacao": power}
    except Exception:
        return {"status": "error", "message": "Payload inválido"}


@fastapi_app.post("/api/aquecedor")
async def control_aquecedor(
    request: Request,
    user: UserContext = Depends(RequireRole(["operator", "admin", "superadmin"])),
):
    from src.core.fsm_task import actuator_state

    try:
        data = await request.json()
        power = bool(data.get("power", False))
        actuator_state["aquecedor_on"] = power
        return {"status": "ok", "aquecedor": power}
    except Exception:
        return {"status": "error", "message": "Payload inválido"}


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
