"""
ChikGuard -- AsyncUploader v1 (I/O Assíncrono para Supabase)
=============================================================
Worker assincrono que salva crops individuais de pintinhos no Supabase
sem bloquear NENHUM frame do pipeline de inferencia.

Arquitetura:
  - Queue asyncio com tamanho maximo (backpressure)
  - Task de fundo (asyncio.Task) consome a fila em loop
  - Upload duplo: Storage (imagem JPEG) + Database (metadados)
  - Retry automatico com backoff exponencial (3 tentativas)
  - Extrator de crop usando mascara de segmentacao (contorno preciso)

Integracao com camera_loop (thread sincrona):
    # No inicio da aplicacao (uma vez):
    uploader = AsyncUploader(supabase_url, supabase_key)
    uploader.start_worker(event_loop)   # event_loop do asyncio

    # No camera_loop (a cada frame, thread sincrona):
    if registry_event:
        uploader.enqueue_sync(frame, track, mask)   # nao bloqueia

    # No shutdown:
    await uploader.stop_worker()

Supabase: a tabela esperada e:
    CREATE TABLE chick_registrations (
        id            BIGSERIAL PRIMARY KEY,
        track_id      INTEGER NOT NULL,
        camera_id     TEXT,
        batch_id      TEXT,
        centroid_x    FLOAT,
        centroid_y    FLOAT,
        bbox          JSONB,
        confidence    FLOAT,
        species       TEXT DEFAULT 'chick',
        image_url     TEXT,
        registered_at TIMESTAMPTZ DEFAULT NOW()
    );
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("chikguard.async_uploader")

# ── Configuracao via ENV ──────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")     # service_role key
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "chick-crops")
DB_TABLE = os.getenv("REGISTRATION_TABLE", "chick_registrations")
ACTIVE_CAMERA_ID = os.getenv("ACTIVE_CAMERA_ID", "galpao-1")
BATCH_ID = os.getenv("BATCH_ID", "lote-1")
QUEUE_MAX_SIZE = int(os.getenv("UPLOAD_QUEUE_SIZE", "200"))  # max crops pendentes
JPEG_QUALITY = int(os.getenv("CROP_JPEG_QUALITY", "85"))
UPLOAD_TIMEOUT_SEC = float(os.getenv("UPLOAD_TIMEOUT", "10.0"))
MAX_RETRIES = int(os.getenv("UPLOAD_MAX_RETRIES", "3"))


# =============================================================================
# Extracao de crop com mascara
# =============================================================================

def extract_crop(
    frame: np.ndarray,
    bbox: List[float],
    mask: Optional[np.ndarray] = None,
    padding: int = 8,
) -> Optional[np.ndarray]:
    """
    Recorta o pintinho do frame, opcionalmente usando a mascara de segmentacao.

    Args:
        frame  : Frame BGR completo
        bbox   : [x1, y1, x2, y2]
        mask   : Mascara binaria (0/255) ou None (usa bbox simples)
        padding: Pixels extras ao redor do bbox para nao cortar as bordas

    Retorna:
        Imagem BGR do crop do pintinho (com fundo preto onde nao e o animal)
        ou None em caso de erro.
    """
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]

    # Aplica padding
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)

    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2].copy()

    if mask is not None:
        try:
            # Redimensiona mascara para o tamanho do crop
            mask_crop = mask[y1:y2, x1:x2]
            if mask_crop.shape[:2] != crop.shape[:2]:
                mask_crop = cv2.resize(
                    mask_crop, (crop.shape[1], crop.shape[0]),
                    interpolation=cv2.INTER_NEAREST,
                )
            # Garante mascara binaria
            if mask_crop.max() <= 1:
                mask_crop = (mask_crop * 255).astype(np.uint8)
            # Aplica mascara: fundo = preto
            mask_3ch = cv2.merge([mask_crop, mask_crop, mask_crop])
            crop = cv2.bitwise_and(crop, mask_3ch)
        except Exception as exc:
            logger.debug("[Crop] Falha ao aplicar mascara: %s — usando bbox", exc)

    return crop


def crop_to_jpeg_bytes(crop: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    """Converte crop NumPy para bytes JPEG."""
    ok, buf = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Falha ao codificar JPEG")
    return buf.tobytes()


# =============================================================================
# Payload de upload
# =============================================================================

@dataclass
class UploadPayload:
    """Dados de um pintinho a ser salvo — colocado na fila pelo camera_loop."""
    track_id: int
    centroid: Tuple[float, float]
    bbox: List[float]
    confidence: float
    species: str
    class_id: int
    crop_jpg: bytes                    # bytes JPEG do crop
    timestamp: float = field(default_factory=time.time)
    extra: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# AsyncUploader — Worker de I/O
# =============================================================================

class AsyncUploader:
    """
    Worker assincrono que consome a fila de crops e salva no Supabase.

    O camera_loop (thread sincrona) chama .enqueue_sync() para adicionar
    itens a fila sem bloquear.

    O worker (asyncio.Task) processa a fila em background:
      1. Upload do JPEG para o Supabase Storage
      2. Insert dos metadados na tabela Supabase
      3. Retry com backoff exponencial em caso de erro
    """

    def __init__(
        self,
        supabase_url: str = SUPABASE_URL,
        supabase_key: str = SUPABASE_KEY,
        storage_bucket: str = STORAGE_BUCKET,
        table: str = DB_TABLE,
    ):
        self._url = supabase_url.rstrip("/")
        self._key = supabase_key
        self._bucket = storage_bucket
        self._table = table
        self._queue: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stats = {"enqueued": 0, "saved": 0, "failed": 0, "dropped": 0}

    # ── Controle ──────────────────────────────────────────────────────────────

    def start_worker(self, loop: asyncio.AbstractEventLoop):
        """
        Inicia o worker assincrono.
        Deve ser chamado com o event loop da aplicacao.
        """
        self._loop = loop
        self._queue = asyncio.Queue(maxsize=QUEUE_MAX_SIZE)
        self._task = loop.create_task(self._worker_loop())
        logger.info(
            "[Uploader] Worker iniciado. bucket=%s table=%s queue_max=%d",
            self._bucket, self._table, QUEUE_MAX_SIZE,
        )

    async def stop_worker(self):
        """Para o worker de forma limpa, processando o que restou na fila."""
        if self._queue:
            await self._queue.join()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[Uploader] Worker parado. Stats: %s", self._stats)

    # ── API para threads sincronas (camera_loop) ──────────────────────────────

    def enqueue_sync(
        self,
        frame: np.ndarray,
        track: Dict[str, Any],
        mask: Optional[np.ndarray] = None,
        species: str = "chick",
    ) -> bool:
        """
        Enfileira um crop para salvamento assincrono.
        NENHUMA I/O acontece aqui — a funcao retorna imediatamente.

        Args:
            frame  : Frame BGR completo
            track  : Dict com track_id, bbox, centroid, confidence, class_id
            mask   : Mascara de segmentacao (opcional)
            species: Especie classificada

        Retorna:
            True se enfileirado, False se fila cheia (crop descartado)
        """
        if self._queue is None or self._loop is None:
            logger.warning("[Uploader] Worker nao iniciado — crop descartado.")
            return False

        # Extrai crop (CPU — rapido, nao e I/O)
        crop = extract_crop(frame, track["bbox"], mask)
        if crop is None:
            return False

        try:
            crop_jpg = crop_to_jpeg_bytes(crop)
        except Exception as exc:
            logger.error("[Uploader] Falha ao encodar JPEG: %s", exc)
            return False

        payload = UploadPayload(
            track_id=track["track_id"],
            centroid=track["centroid"],
            bbox=track["bbox"],
            confidence=track.get("confidence", 0.0),
            species=species,
            class_id=track.get("class_id", 0),
            crop_jpg=crop_jpg,
        )

        # Usa call_soon_threadsafe para enfileirar de forma thread-safe
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._safe_enqueue(payload), self._loop
            )
            result = future.result(timeout=0.05)   # nao espera mais de 50ms
            if result:
                self._stats["enqueued"] += 1
            else:
                self._stats["dropped"] += 1
            return result
        except Exception as exc:
            logger.debug("[Uploader] enqueue_sync timeout/falha: %s", exc)
            self._stats["dropped"] += 1
            return False

    async def _safe_enqueue(self, payload: UploadPayload) -> bool:
        """Enfileira sem bloquear (put_nowait — descarta se cheio)."""
        try:
            self._queue.put_nowait(payload)
            return True
        except asyncio.QueueFull:
            return False

    # ── Worker interno ────────────────────────────────────────────────────────

    async def _worker_loop(self):
        """Loop principal do worker. Processa items da fila indefinidamente."""
        logger.info("[Uploader] Worker loop iniciado.")
        while True:
            try:
                payload: UploadPayload = await self._queue.get()
                try:
                    await self._save_with_retry(payload)
                    self._stats["saved"] += 1
                except Exception as exc:
                    logger.error(
                        "[Uploader] Falha definitiva track_id=%d: %s",
                        payload.track_id, exc,
                    )
                    self._stats["failed"] += 1
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("[Uploader] Erro inesperado no worker: %s", exc)

    async def _save_with_retry(self, payload: UploadPayload):
        """Tenta salvar com retry + backoff exponencial."""
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                image_url = await self._upload_storage(payload)
                await self._insert_database(payload, image_url)
                logger.debug(
                    "[Uploader] track_id=%d salvo em %d tentativa(s).",
                    payload.track_id, attempt,
                )
                return
            except Exception as exc:
                last_exc = exc
                wait = 2 ** (attempt - 1)   # 1s, 2s, 4s
                logger.warning(
                    "[Uploader] Tentativa %d/%d falhou para track_id=%d: %s — aguardando %ds",
                    attempt, MAX_RETRIES, payload.track_id, exc, wait,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(f"Todas as {MAX_RETRIES} tentativas falharam: {last_exc}")

    # ── Supabase Storage ──────────────────────────────────────────────────────

    async def _upload_storage(self, payload: UploadPayload) -> str:
        """
        Faz upload do crop JPEG para o Supabase Storage.
        Retorna a URL publica do arquivo.
        """
        try:
            import aiohttp
        except ImportError:
            # Fallback sincrono via requests (menos ideal, mas funciona)
            return await self._upload_storage_requests(payload)

        ts = int(payload.timestamp)
        path = f"{ACTIVE_CAMERA_ID}/{BATCH_ID}/chick_{payload.track_id}_{ts}.jpg"
        url = f"{self._url}/storage/v1/object/{self._bucket}/{path}"
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "image/jpeg",
            "x-upsert": "true",   # sobrescreve se ja existir
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=payload.crop_jpg,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=UPLOAD_TIMEOUT_SEC),
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    raise RuntimeError(f"Storage HTTP {resp.status}: {body[:200]}")

        public_url = f"{self._url}/storage/v1/object/public/{self._bucket}/{path}"
        return public_url

    async def _upload_storage_requests(self, payload: UploadPayload) -> str:
        """Fallback sincrono via requests (sem aiohttp instalado)."""
        import requests

        ts = int(payload.timestamp)
        path = f"{ACTIVE_CAMERA_ID}/{BATCH_ID}/chick_{payload.track_id}_{ts}.jpg"
        url = f"{self._url}/storage/v1/object/{self._bucket}/{path}"

        loop = asyncio.get_event_loop()

        def _do_upload():
            resp = requests.post(
                url,
                data=payload.crop_jpg,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "Content-Type": "image/jpeg",
                    "x-upsert": "true",
                },
                timeout=UPLOAD_TIMEOUT_SEC,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Storage HTTP {resp.status_code}: {resp.text[:200]}")

        await loop.run_in_executor(None, _do_upload)
        return f"{self._url}/storage/v1/object/public/{self._bucket}/{path}"

    # ── Supabase Database ─────────────────────────────────────────────────────

    async def _insert_database(self, payload: UploadPayload, image_url: str):
        """
        Insere registro na tabela Supabase via REST API.
        Usa ON CONFLICT DO NOTHING para garantia extra contra duplicatas.
        """
        try:
            import aiohttp
        except ImportError:
            await self._insert_database_requests(payload, image_url)
            return

        url = f"{self._url}/rest/v1/{self._table}"
        headers = {
            "Authorization": f"Bearer {self._key}",
            "apikey": self._key,
            "Content-Type": "application/json",
            "Prefer": "return=minimal,resolution=ignore-duplicates",
        }
        body = {
            "track_id": payload.track_id,
            "camera_id": ACTIVE_CAMERA_ID,
            "batch_id": BATCH_ID,
            "centroid_x": round(payload.centroid[0], 2),
            "centroid_y": round(payload.centroid[1], 2),
            "bbox": {"x1": payload.bbox[0], "y1": payload.bbox[1],
                     "x2": payload.bbox[2], "y2": payload.bbox[3]},
            "confidence": round(float(payload.confidence), 4),
            "species": payload.species,
            "image_url": image_url,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=UPLOAD_TIMEOUT_SEC),
            ) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"DB HTTP {resp.status}: {text[:200]}")

    async def _insert_database_requests(self, payload: UploadPayload, image_url: str):
        """Fallback sincrono para insert no banco."""
        import requests

        url = f"{self._url}/rest/v1/{self._table}"
        body = {
            "track_id": payload.track_id,
            "camera_id": ACTIVE_CAMERA_ID,
            "batch_id": BATCH_ID,
            "centroid_x": round(payload.centroid[0], 2),
            "centroid_y": round(payload.centroid[1], 2),
            "bbox": {"x1": payload.bbox[0], "y1": payload.bbox[1],
                     "x2": payload.bbox[2], "y2": payload.bbox[3]},
            "confidence": round(float(payload.confidence), 4),
            "species": payload.species,
            "image_url": image_url,
        }

        loop = asyncio.get_event_loop()

        def _do_insert():
            resp = requests.post(
                url, json=body,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "apikey": self._key,
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal,resolution=ignore-duplicates",
                },
                timeout=UPLOAD_TIMEOUT_SEC,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"DB HTTP {resp.status_code}: {resp.text[:200]}")

        await loop.run_in_executor(None, _do_insert)

    # ── Stats / Debug ─────────────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    @property
    def queue_size(self) -> int:
        return self._queue.qsize() if self._queue else 0
