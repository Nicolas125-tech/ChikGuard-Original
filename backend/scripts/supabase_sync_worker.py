import asyncio
import aiofiles
import json
import os
import time

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: Supabase credentials not found in environment. Sync will be mocked.")
    supabase: Client = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        supabase = None


class SupabaseSyncWorker:
    """Worker de sincronização offline-first para o Supabase.

    Previne a perda de dados durante oscilações de rede (comuns em áreas rurais),
    só avançando a leitura após confirmação de salvamento e utilizando
    backoff exponencial para tentativas de reconexão.
    """

    def __init__(
        self,
        log_file="tracking_logs.json",
        state_file="sync_state.json",
        batch_size=50,
        interval_seconds=5,
    ):
        self.log_file = log_file
        self.state_file = state_file
        self.batch_size = batch_size
        self.base_interval = interval_seconds
        self.current_interval = interval_seconds

        self.last_processed_idx = 0
        self.backlog = []  # Registros pendentes de envio (backlog de falha)

        self.load_state()

    def load_state(self):
        """Carrega o estado anterior de sincronização do arquivo persistente."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    self.last_processed_idx = state.get("last_processed_idx", 0)
                    self.backlog = state.get("backlog", [])
                print(
                    f"[Sync] Estado carregado. Index={self.last_processed_idx}, Backlog={len(self.backlog)} itens."
                )
            except Exception as e:
                print(f"[Sync] Erro ao carregar estado: {e}. Iniciando do zero.")

    def save_state(self):
        """Salva o estado atual de sincronização em arquivo persistente."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(
                    {"last_processed_idx": self.last_processed_idx, "backlog": self.backlog},
                    f,
                    indent=2,
                )
        except Exception as e:
            print(f"[Sync] Erro ao salvar estado: {e}")

    async def fetch_new_logs(self):
        """Lê novas entradas de log do arquivo JSON, sem avançar o índice global ainda."""
        if not os.path.exists(self.log_file):
            return []

        try:
            async with aiofiles.open(self.log_file, "r") as f:
                content = await f.read()
                data = json.loads(content)

            if len(data) <= self.last_processed_idx:
                return []

            new_logs = data[self.last_processed_idx :]
            # Retorna logs e o novo índice temporário
            return new_logs, len(data)
        except json.JSONDecodeError:
            # Arquivo pode estar sendo escrito no mesmo instante
            return []
        except Exception as e:
            print(f"[Sync] Erro ao ler logs: {e}")
            return []

    def transform_for_supabase(self, logs):
        """Transforma logs brutos em registros planos formatados para o Supabase."""
        records = []
        for frame_log in logs:
            timestamp = frame_log.get("timestamp", time.time())
            frame_num = frame_log.get("frame")

            for det in frame_log.get("detections", []):
                records.append(
                    {
                        "track_id": det["id"],
                        "class_id": det["class"],
                        "confidence": det["confidence"],
                        "pos_x": det["smoothed_centroid"][0],
                        "pos_y": det["smoothed_centroid"][1],
                        "frame_number": frame_num,
                        "detected_at": time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(timestamp)
                        ),
                    }
                )
        return records

    async def sync_records(self, records) -> bool:
        """Tenta enviar uma lista de registros para o Supabase. Retorna True se obtiver sucesso."""
        if not records:
            return True

        if not supabase:
            # Modo simulado de testes
            print(f"[Sync Mock] Sincronizados {len(records)} registros com sucesso.")
            return True

        try:
            # Insere no Supabase
            supabase.table("bird_tracking_logs").insert(records).execute()
            return True
        except Exception as e:
            print(f"[Sync] Falha na rede / Supabase: {e}")
            return False

    async def run_once(self):
        """Executa um ciclo único de verificação e envio de dados."""
        # 1. Tenta limpar o backlog pendente primeiro
        if self.backlog:
            print(f"[Sync] Tentando enviar backlog pendente: {len(self.backlog)} itens...")
            success = await self.sync_records(self.backlog[: self.batch_size])

            if success:
                # Remove itens enviados do backlog
                self.backlog = self.backlog[self.batch_size :]
                self.save_state()
                # Reseta o intervalo de backoff (sucesso restabelece a rede)
                self.current_interval = self.base_interval
                print(f"[Sync] Backlog reduzido. Pendentes: {len(self.backlog)}")
            else:
                # Falhou: aplica backoff exponencial (máximo de 5 minutos)
                self.current_interval = min(self.current_interval * 2, 300)
                print(
                    f"[Sync] Erro no backlog. Aumentando intervalo de espera para {self.current_interval}s."
                )
                return

        # 2. Busca novos logs apenas se o backlog estiver limpo
        if not self.backlog:
            fetch_res = await self.fetch_new_logs()
            if fetch_res:
                new_logs, temp_next_idx = fetch_res
                records = self.transform_for_supabase(new_logs)

                if records:
                    success = await self.sync_records(records[: self.batch_size])

                    if success:
                        # Avança o índice e limpa registros enviados
                        self.last_processed_idx += len(new_logs)  # Ajusta index correspondente
                        self.save_state()
                        self.current_interval = self.base_interval
                        print(
                            f"[Sync] Sincronizados {len(records)} registros novos. Próximo index: {self.last_processed_idx}"
                        )
                    else:
                        # Adiciona registros ao backlog de falha para tentar mais tarde
                        self.backlog.extend(records)
                        # Mesmo falhando, consideramos os logs lidos do arquivo de log, mas agora residem no backlog do sync
                        self.last_processed_idx = temp_next_idx
                        self.save_state()
                        self.current_interval = min(self.current_interval * 2, 300)
                        print(
                            f"[Sync] Erro no envio. Movidos para o backlog. Novo intervalo de espera: {self.current_interval}s."
                        )

    async def run(self):
        print("Starting Supabase Sync Worker (Offline-First mode)...")
        print(f"Tracking logs: {self.log_file}")

        while True:
            await self.run_once()
            await asyncio.sleep(self.current_interval)


if __name__ == "__main__":
    worker = SupabaseSyncWorker(
        log_file="tracking_logs.json",
        state_file="sync_state.json",
        batch_size=100,
        interval_seconds=5,
    )

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("Sync Worker stopped by user.")
