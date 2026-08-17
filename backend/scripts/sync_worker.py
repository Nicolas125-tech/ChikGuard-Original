import logging
import os
import socket
import time
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import create_engine, MetaData, Table, update, select, or_, and_, bindparam
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
    raise ValueError(
        "As variaveis SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY sao obrigatorias."
    )

# Setup do SQLAlchemy (Standalone)
engine = create_engine(LOCAL_DB_URL)
SessionLocal = sessionmaker(bind=engine)
metadata = MetaData()


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
    Busca registros nao sincronizados via SQL Core para evitar vulnerabilidades de injecao.
    Traz PENDING ou FAILED cujo ultimo erro ocorreu ha mais de X minutos.
    """

    # 🛡️ Sentinel: Validate table_name against an allowlist to prevent SQL Injection
    ALLOWED_TABLES = {"sensor_reading", "event_log", "bird_snapshot"}
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table_name: {table_name}")

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=MAX_BACKOFF_MINUTES)
    # Remove timezone info para SQLite datetime string compatibility (para a query baseada em string/core)
    cutoff_str = cutoff.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

    # Reflect safe table
    table = Table(table_name, metadata, autoload_with=engine)

    stmt = (
        select(table)
        .where(
            or_(
                table.c.sync_status == "PENDING",
                and_(
                    table.c.sync_status == "FAILED",
                    table.c.last_sync_attempt < cutoff_str,
                ),
            )
        )
        .order_by(table.c.id.asc())
        .limit(limit)
    )

    result = session.execute(stmt).mappings().all()
    return [dict(r) for r in result]


def mark_records(session, table_name, ids, status):
    """Atualiza o status em Bulk localmente."""
    if not ids:
        return

    # 🛡️ Sentinel: Validate table_name against an allowlist to prevent SQL Injection
    ALLOWED_TABLES = {"sensor_reading", "event_log", "bird_snapshot"}
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table_name: {table_name}")

    # Para updates em bulk via core e ORM no sqlite com datetime, precisamos passar o objeto datetime nativo
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    table = Table(table_name, metadata, autoload_with=engine)

    stmt = (
        update(table)
        .where(table.c.id == bindparam('b_id'))
        .values(sync_status=bindparam('b_status'), last_sync_attempt=bindparam('b_now'))
    )

    bulk_data = [{"b_id": i, "b_status": status, "b_now": now} for i in ids]
    session.execute(stmt, bulk_data)
    session.commit()


def sync_table(session, table_name):
    records = get_pending_records(session, table_name, BATCH_SIZE)
    if not records:
        return 0

    ids_to_sync = [r["id"] for r in records]

    # Preparar payload (removemos colunas exclusivas da borda local, como as de status)
    payload = []
    for r in records:
        clean_record = {
            k: v for k, v in r.items() if k not in ("sync_status", "last_sync_attempt")
        }
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
            logger.info(
                f"[{table_name}] Sincronizados com sucesso: {len(ids_to_sync)} registros."
            )
            return len(ids_to_sync)
        else:
            logger.warning(
                f"[{table_name}] Falha na API: {response.status_code} - {response.text}"
            )
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
