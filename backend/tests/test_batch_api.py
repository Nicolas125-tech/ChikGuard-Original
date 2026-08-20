import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
import unittest.mock as mock
from datetime import datetime

import jwt
import pytest
from flask import Flask

os.environ["SUPABASE_JWT_SECRET"] = os.environ.get(
    "SUPABASE_JWT_SECRET", "dummy_secret_dummy_secret_dummy_secret"
)

sys_modules_mock = mock.patch.dict("sys.modules", {"cv2": mock.MagicMock()})
sys_modules_mock.start()

from database import Batch, BatchLogbook, db  # noqa: E402
from src.api.batch_api import create_batch_blueprint  # noqa: E402


@pytest.fixture
def mock_deps():
    mock_audit = mock.MagicMock()
    mock_guard = mock.MagicMock(return_value=(True, None))
    return {
        "audit_fn": mock_audit,
        "guard_critical_action": mock_guard,
        "utcnow_fn": datetime.utcnow,
        "active_camera_id": "galpao-1",
    }


@pytest.fixture
def test_app(mock_deps):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    bp = create_batch_blueprint(mock_deps)
    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(test_app):
    with test_app.test_client() as client:
        yield client


@pytest.fixture
def auth_headers():
    token = jwt.encode(
        {
            "sub": "user_id_test",
            "aud": "authenticated",
            "app_metadata": {"role": "admin", "tenant_id": 1},
        },
        os.environ["SUPABASE_JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_get_batches_empty(client, auth_headers):
    resp = client.get("/api/batches", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json == []


def test_start_batch(client, auth_headers, mock_deps, test_app):
    resp = client.post(
        "/api/batches",
        headers=auth_headers,
        json={"name": "Lote Teste 1", "notes": "Notas teste"},
    )
    assert resp.status_code == 201
    assert resp.json["msg"] == "Lote iniciado com sucesso"
    assert resp.json["batch"]["name"] == "Lote Teste 1"
    assert resp.json["batch"]["notes"] == "Notas teste"
    assert resp.json["batch"]["active"] is True

    mock_deps["audit_fn"].assert_called_with(
        "batch_started", details={"name": "Lote Teste 1"}
    )


def test_get_active_batch(client, auth_headers):
    # Setup initial batch
    client.post(
        "/api/batches", headers=auth_headers, json={"name": "Lote Ativo"}
    )

    resp = client.get("/api/batches/active", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json["name"] == "Lote Ativo"
    assert resp.json["active"] is True
    assert "age_days" in resp.json


def test_get_active_batch_not_found(client, auth_headers, test_app):
    with test_app.app_context():
        # Make sure no batches are active
        Batch.query.update({Batch.active: False})
        db.session.commit()

    resp = client.get("/api/batches/active", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json["msg"] == "Nenhum lote ativo no momento"


def test_close_batch(client, auth_headers, mock_deps, test_app):
    # Setup initial batch
    client.post(
        "/api/batches",
        headers=auth_headers,
        json={"name": "Lote Para Fechar"},
    )

    resp = client.post("/api/batches/close", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json["msg"] == "Lote encerrado com sucesso"
    assert resp.json["batch"]["active"] is False

    with test_app.app_context():
        active = Batch.query.filter_by(active=True).first()
        assert active is None


def test_close_batch_not_found(client, auth_headers, test_app):
    with test_app.app_context():
        Batch.query.update({Batch.active: False})
        db.session.commit()

    resp = client.post("/api/batches/close", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json["msg"] == "Nenhum lote ativo para encerrar"


def test_add_logbook(client, auth_headers, test_app):
    # Create batch
    resp_batch = client.post(
        "/api/batches", headers=auth_headers, json={"name": "Lote Logbook"}
    )
    batch_id = resp_batch.json["batch"]["id"]

    resp = client.post(
        f"/api/batches/{batch_id}/logbook",
        headers=auth_headers,
        json={"note": "Nota importante"},
    )
    assert resp.status_code == 201
    assert resp.json["msg"] == "Nota adicionada ao diário do lote"
    assert resp.json["log"]["note"] == "Nota importante"
    assert resp.json["log"]["batch_id"] == batch_id

    with test_app.app_context():
        logs = BatchLogbook.query.filter_by(batch_id=batch_id).all()
        assert len(logs) == 1
        assert logs[0].note == "Nota importante"


def test_add_logbook_empty_note(client, auth_headers):
    # Create batch
    resp_batch = client.post(
        "/api/batches", headers=auth_headers, json={"name": "Lote Logbook"}
    )
    batch_id = resp_batch.json["batch"]["id"]

    resp = client.post(
        f"/api/batches/{batch_id}/logbook",
        headers=auth_headers,
        json={"note": "   "},
    )
    assert resp.status_code == 400
    assert resp.json["msg"] == "Nota é obrigatória"


def test_start_batch_closes_previous(client, auth_headers, test_app):
    client.post("/api/batches", headers=auth_headers, json={"name": "Lote 1"})

    with test_app.app_context():
        active = Batch.query.filter_by(active=True).all()
        assert len(active) == 1
        assert active[0].name == "Lote 1"

    client.post("/api/batches", headers=auth_headers, json={"name": "Lote 2"})

    with test_app.app_context():
        active = Batch.query.filter_by(active=True).all()
        assert len(active) == 1
        assert active[0].name == "Lote 2"

        all_batches = Batch.query.all()
        assert len(all_batches) == 2
        batch1 = next(b for b in all_batches if b.name == "Lote 1")
        assert batch1.active is False


def test_endpoints_unauthorized(client):
    assert client.get("/api/batches").status_code == 401
    assert client.get("/api/batches/active").status_code == 401
    assert client.post("/api/batches").status_code == 401
    assert client.post("/api/batches/close").status_code == 401
    assert client.post("/api/batches/1/logbook").status_code == 401


def test_guard_failure(client, auth_headers, mock_deps):
    mock_deps["guard_critical_action"].return_value = (
        False,
        ({"error": "Forbidden"}, 403),
    )

    assert client.post("/api/batches", headers=auth_headers).status_code == 403
    assert (
        client.post("/api/batches/close", headers=auth_headers).status_code
        == 403
    )
    assert (
        client.post(
            "/api/batches/1/logbook", headers=auth_headers
        ).status_code
        == 403
    )
