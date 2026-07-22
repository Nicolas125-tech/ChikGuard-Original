import asyncio
import logging
from datetime import datetime, timezone
from database import SensorReading
from sqlalchemy import update

logger = logging.getLogger("chikguard.sensor_sync")


class SensorSyncWorker:
    """
    Worker que implementa a lógica de fallback e sincronização assíncrona (Store & Forward).
    Varre o banco SQLite local do gateway por leituras pendentes e as envia para o Supabase
    apenas quando há conexão com a internet ativa, aplicando backoff exponencial em caso de falha.
    """

    def __init__(self, db_session=None, supabase_client=None, interval_seconds=5):
        self.db_session = db_session
        self.supabase = supabase_client
        self.base_interval = interval_seconds
        self.current_interval = interval_seconds

    async def run_once(self):
        """
        Executa um único ciclo de sincronização de dados pendentes.
        """
        # Se uma sessão foi injetada (Testes), usa ela. Caso contrário, abre uma nova do local
        session = self.db_session
        created_session = False

        if session is None:
            from src.db.session import SessionLocal

            session = SessionLocal()
            created_session = True

        try:
            # 1. Puxa do SQLite leituras pendentes ou que falharam em lotes (batch)
            readings = (
                session.query(SensorReading)
                .filter(SensorReading.sync_status.in_(["PENDING", "FAILED"]))
                .order_by(SensorReading.timestamp.asc())
                .limit(100)
                .all()
            )

            if not readings:
                return

            # 2. Transforma as leituras no payload plano do Supabase para relatórios históricos
            records = []
            for r in readings:
                records.append(
                    {
                        "camera_id": r.camera_id,
                        "temperature_c": r.temperature_c,
                        "humidity_pct": r.humidity_pct,
                        "ammonia_ppm": r.ammonia_ppm,
                        "source": r.source,
                        "created_at": (
                            r.timestamp.astimezone(timezone.utc).isoformat()
                            if r.timestamp
                            else datetime.now(timezone.utc).isoformat()
                        ),
                    }
                )

            # 3. Tenta persistir remotamente no Supabase
            try:
                if self.supabase is not None:
                    # Usando cliente injetado (ex: nos testes)
                    self.supabase.table("sensor_readings").insert(records).execute()
                else:
                    # Usando cliente global instanciado no worker de logs do sistema
                    from scripts.supabase_sync_worker import supabase as global_supabase

                    if global_supabase is not None:
                        global_supabase.table("sensor_readings").insert(
                            records
                        ).execute()
                    else:
                        raise ConnectionError(
                            "Cliente Supabase não inicializado no Gateway."
                        )

                # Sucesso: atualiza localmente para SYNCED em lote
                ids = [r.id for r in readings]
                session.execute(
                    update(SensorReading)
                    .where(SensorReading.id.in_(ids))
                    .values(
                        sync_status="SYNCED",
                        last_sync_attempt=datetime.now(timezone.utc),
                    )
                )

                session.commit()
                # Reseta o tempo de espera para o valor padrão (reconexão restabelecida)
                self.current_interval = self.base_interval
                logger.info(
                    f"[Sensor Sync] Sincronizados {len(readings)} registros de sensores com o Supabase."
                )

            except Exception as net_err:
                # Falha de rede/Supabase: marca local como FAILED e aplica backoff
                session.rollback()
                ids = [r.id for r in readings]
                session.execute(
                    update(SensorReading)
                    .where(SensorReading.id.in_(ids))
                    .values(
                        sync_status="FAILED",
                        last_sync_attempt=datetime.now(timezone.utc),
                    )
                )

                session.commit()
                # Dobra o tempo de espera até o máximo de 5 minutos (300 segundos)
                self.current_interval = min(self.current_interval * 2, 300)
                logger.warning(
                    f"[Sensor Sync] Falha de comunicação com a Nuvem. Registros marcados para retentativa local. "
                    f"Erro: {net_err}. Aplicando backoff. Novo intervalo: {self.current_interval}s."
                )

        except Exception as e:
            logger.error(f"[Sensor Sync] Erro crítico no worker de sincronização: {e}")
            if created_session:
                session.rollback()
        finally:
            if created_session:
                session.close()

    async def run(self):
        """
        Loop contínuo assíncrono para execução em background do worker.
        """
        logger.info("Iniciando Sensor Sync Worker (Offline-First para Supabase)...")
        while True:
            await self.run_once()
            await asyncio.sleep(self.current_interval)
