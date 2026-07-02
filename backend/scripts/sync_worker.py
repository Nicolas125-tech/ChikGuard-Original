import logging
import os
import socket
import time
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] SYNC_WORKER: %(message)s"
)
logger = logging.getLogger(__name__)

# Variáveis de Ambiente Críticas
LOCAL_DB_URL = os.getenv("DATABASE_URL", "sqlite:///../instance/chikguard.db")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

BATCH_SIZE = 500
SYNC_INTERVAL_SEC = 30
MAX_BACKOFF_MINUTES = 15

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("As variaveis SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY sao obrigatorias.")

# Setup do SQLAlchemy (Standalone)
engine = create_engine(LOCAL_DB_URL)
SessionLocal = sessionmaker(bind=engine)


def check_internet(host="8.8.8.8", port=53, timeout=3):
    """Verifica conexao via socket TCP, muito mais rapido que HTTP GET."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


def get_pending_records(session, table_name, limit):
    """
    Busca registros nao sincronizados via SQL RAW bruto para maxima performance.
    Traz PENDING ou FAILED cujo ultimo erro ocorreu ha mais de X minutos.
    """
    sql = f"""
        SELECT * FROM {table_name}
        WHERE sync_status = 'PENDING' 
           OR (sync_status = 'FAILED' AND last_sync_attempt < :cutoff_time)
        ORDER BY id ASC
        LIMIT :limit
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=MAX_BACKOFF_MINUTES)
    # Remove timezone info para SQLite datetime string compatibility
    cutoff_str = cutoff.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

    result = session.execute(text(sql), {"cutoff_time": cutoff_str, "limit": limit}).mappings().all()
    return [dict(r) for r in result]


def mark_records(session, table_name, ids, status):
    """Atualiza o status em Bulk localmente."""
    if not ids:
        return
    now_str = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    params = {"status": status, "now_str": now_str}
    id_params = []
    for i, id_val in enumerate(ids):
        p_name = f"id_{i}"
        id_params.append(f":{p_name}")
        params[p_name] = id_val
    ids_str_params = ",".join(id_params)

    sql = f"""
        UPDATE {table_name} 
        SET sync_status = :status, last_sync_attempt = :now_str
        WHERE id IN ({ids_str_params})
    """
    session.execute(text(sql), params)
    session.commit()


def sync_table(session, table_name):
    records = get_pending_records(session, table_name, BATCH_SIZE)
    if not records:
        return 0

    ids_to_sync = [r["id"] for r in records]

    # Preparar payload (removemos colunas exclusivas da borda local, como as de status)
    payload = []
    for r in records:
        clean_record = {k: v for k, v in r.items() if k not in ("sync_status", "last_sync_attempt")}
        payload.append(clean_record)

    # Supabase PostgREST Bulk Insert endpoint
    endpoint = f"{SUPABASE_URL}/rest/v1/{table_name}"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",  # Otimiza banda: manda o DB nao retornar os registros salvos
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)

        if response.status_code in (200, 201, 204):
            mark_records(session, table_name, ids_to_sync, "SYNCED")
            logger.info(f"[{table_name}] Sincronizados com sucesso: {len(ids_to_sync)} registros.")
            return len(ids_to_sync)
        else:
            logger.warning(f"[{table_name}] Falha na API: {response.status_code} - {response.text}")
            mark_records(session, table_name, ids_to_sync, "FAILED")
            return 0

    except requests.exceptions.RequestException as e:
        logger.error(f"[{table_name}] Falha de conexao/Timeout: {e}")
        mark_records(session, table_name, ids_to_sync, "FAILED")
        return 0


def run_sync_loop():
    logger.info("Sync Worker inicializado.")
    tables_to_sync = ["sensor_reading", "event_log", "bird_snapshot"]

    while True:
        if not check_internet():
            logger.warning("Sem conexao com a internet. Aguardando...")
            time.sleep(SYNC_INTERVAL_SEC)
            continue

        try:
            with SessionLocal() as session:
                total_synced = 0
                for table in tables_to_sync:
                    total_synced += sync_table(session, table)

                if total_synced < (BATCH_SIZE * len(tables_to_sync)):
                    time.sleep(SYNC_INTERVAL_SEC)

        except Exception as e:
            logger.error(f"Falha inesperada no worker loop: {e}")
            time.sleep(SYNC_INTERVAL_SEC)


if __name__ == "__main__":
    run_sync_loop()
