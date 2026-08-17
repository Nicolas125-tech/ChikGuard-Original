import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker

import os
os.environ["SUPABASE_URL"] = "http://dummy"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "dummy"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
import sync_worker

def test_mark_records_parameterized():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    table_name = "sensor_reading"

    table = Table(
        table_name, metadata,
        Column("id", Integer, primary_key=True),
        Column("sync_status", String),
        Column("last_sync_attempt", DateTime)
    )
    metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session.execute(table.insert(), [
        {"id": 1, "sync_status": "PENDING", "last_sync_attempt": now},
        {"id": 2, "sync_status": "PENDING", "last_sync_attempt": now},
        {"id": 3, "sync_status": "PENDING", "last_sync_attempt": now}
    ])
    session.commit()

    sync_worker.engine = engine
    sync_worker.metadata = metadata
    sync_worker.SessionLocal = SessionLocal

    sync_worker.mark_records(session, table_name, [1, 2], "SYNCED")

    results = session.execute(table.select()).mappings().all()
    assert results[0]["sync_status"] == "SYNCED"
    assert results[1]["sync_status"] == "SYNCED"
    assert results[2]["sync_status"] == "PENDING"
