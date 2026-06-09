from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_mixin


def _utcnow():
    return datetime.now(timezone.utc)


@declarative_mixin
class SyncMixin:
    """
    Mixin abstrato que adiciona capacidades de Store & Forward aos modelos.
    """

    sync_status = Column(String(20), default="PENDING", nullable=False, index=True)
    last_sync_attempt = Column(DateTime, nullable=True)

    def mark_synced(self):
        self.sync_status = "SYNCED"
        self.last_sync_attempt = _utcnow()

    def mark_failed(self):
        self.sync_status = "FAILED"
        self.last_sync_attempt = _utcnow()
