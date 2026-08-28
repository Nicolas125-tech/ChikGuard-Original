"""
nosql_session.py — MongoDB Async Connection Manager (Singleton)
================================================================
Manages a single AsyncIOMotorClient instance for the entire application.
Provides:
  - get_nosql_db()  → returns the Motor database for FastAPI dependency injection
  - MongoDBBatchWriter → accumulates documents and flushes them via insert_many
                          for high-throughput CV pipeline writes
"""

import asyncio
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.core.config import load_settings

logger = logging.getLogger("chikguard.nosql_session")


class _MongoSingleton:
    """Thread-safe Singleton for the Motor (async MongoDB) client."""

    _instance: Optional["_MongoSingleton"] = None
    _lock = threading.Lock()

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    _initialized: bool = False

    def __new__(cls) -> "_MongoSingleton":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def init(self, uri: Optional[str] = None) -> None:
        """Initializes the Motor client. Safe to call multiple times (idempotent)."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            settings = load_settings()
            mongo_uri = uri or settings.mongodb_uri

            try:
                self.client = AsyncIOMotorClient(
                    mongo_uri,
                    maxPoolSize=50,
                    minPoolSize=5,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                )
                # Extract DB name from URI or fallback
                db_name = mongo_uri.rsplit("/", 1)[-1].split("?")[0] or "chikguard"
                self.db = self.client[db_name]
                self._initialized = True
                logger.info(f"MongoDB connected → {db_name} (pool: 5-50)")
            except Exception as exc:
                logger.error(f"Failed to connect to MongoDB: {exc}")
                raise

    async def ping(self) -> bool:
        """Health check — returns True if MongoDB responds."""
        try:
            if self.client is None:
                return False
            await self.client.admin.command("ping")
            return True
        except Exception as exc:
            logger.warning(f"MongoDB ping failed: {exc}")
            return False

    async def close(self) -> None:
        """Gracefully close the Motor client."""
        if self.client is not None:
            self.client.close()
            self._initialized = False
            logger.info("MongoDB connection closed.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_singleton = _MongoSingleton()


def init_nosql(uri: Optional[str] = None) -> None:
    """Call once at application startup (e.g. FastAPI lifespan)."""
    _singleton.init(uri)


def get_nosql_db() -> AsyncIOMotorDatabase:
    """
    Returns the Motor database instance.
    Usage as a FastAPI dependency:
        db = Depends(get_nosql_db)
    """
    if not _singleton._initialized:
        _singleton.init()
    return _singleton.db


async def close_nosql() -> None:
    """Call at application shutdown."""
    await _singleton.close()


async def nosql_health_check() -> bool:
    """Returns True if MongoDB is reachable."""
    return await _singleton.ping()


# ---------------------------------------------------------------------------
# Batch Writer — buffers CV pipeline documents and flushes via insert_many
# ---------------------------------------------------------------------------

class MongoDBBatchWriter:
    """
    Accumulates documents in memory and flushes them to a MongoDB collection
    when the buffer reaches `batch_size` or `flush_interval_sec` elapses.

    Designed for the CV pipeline's high-frequency writes (detections,
    track points, heatmap coordinates).

    Usage (from a sync thread like cv_runner):
        writer = MongoDBBatchWriter("cv_detections", batch_size=50)
        writer.add({"track_id": 1, "box": [10,20,30,40], ...})
        # Flushing happens automatically; call flush_sync() on shutdown.
    """

    def __init__(
        self,
        collection_name: str,
        batch_size: int = 50,
        flush_interval_sec: float = 10.0,
    ):
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec

        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = time.monotonic()

    def add(self, document: Dict[str, Any]) -> None:
        """Thread-safe append. Auto-flushes when thresholds are met."""
        with self._lock:
            self._buffer.append(document)
            should_flush = (
                len(self._buffer) >= self.batch_size
                or (time.monotonic() - self._last_flush) >= self.flush_interval_sec
            )

        if should_flush:
            self.flush_sync()

    def add_many(self, documents: List[Dict[str, Any]]) -> None:
        """Thread-safe batch append."""
        with self._lock:
            self._buffer.extend(documents)
            should_flush = (
                len(self._buffer) >= self.batch_size
                or (time.monotonic() - self._last_flush) >= self.flush_interval_sec
            )

        if should_flush:
            self.flush_sync()

    def flush_sync(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """
        Flushes the buffer to MongoDB. Can be called from a sync thread —
        schedules the async insert on the provided (or running) event loop.
        """
        with self._lock:
            if not self._buffer:
                return
            docs = self._buffer.copy()
            self._buffer.clear()
            self._last_flush = time.monotonic()

        target_loop = loop
        if target_loop is None:
            try:
                target_loop = asyncio.get_running_loop()
            except RuntimeError:
                target_loop = None

        if target_loop is not None and target_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._flush_async(docs), target_loop)
        else:
            # Fallback: create a temporary loop (edge case for shutdown)
            try:
                asyncio.run(self._flush_async(docs))
            except RuntimeError:
                logger.warning(
                    f"Could not flush {len(docs)} docs to {self.collection_name} — no event loop."
                )

    async def _flush_async(self, docs: List[Dict[str, Any]]) -> None:
        """Performs the actual insert_many into MongoDB."""
        try:
            db = get_nosql_db()
            collection = db[self.collection_name]
            await collection.insert_many(docs, ordered=False)
            logger.debug(
                f"Flushed {len(docs)} docs → {self.collection_name}"
            )
        except Exception as exc:
            logger.error(
                f"MongoDB batch insert failed ({self.collection_name}): {exc}"
            )
