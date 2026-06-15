from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

from mixins import SyncMixin

db = SQLAlchemy()


# Tabela de Inquilinos (Empresas/Cooperativas) para Fase 3 (SaaS Multi-Tenant)
class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "active": self.active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class RolePermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(30), nullable=False, index=True)
    permission = db.Column(db.String(80), nullable=False, index=True)
    allowed = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (db.UniqueConstraint("role", "permission", name="uq_role_permission"),)

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "permission": self.permission,
            "allowed": self.allowed,
        }


# NOVA TABELA: Histórico de Leituras
class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    temperatura = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Data e hora automática

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "temp": self.temperatura,
            "status": self.status,
            "hora": self.timestamp.strftime("%H:%M:%S"),
            "data": self.timestamp.strftime("%d/%m/%Y"),
        }


class BirdSnapshot(db.Model, SyncMixin):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    bird_uid = db.Column(db.Integer, nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)
    x1 = db.Column(db.Integer, nullable=False)
    y1 = db.Column(db.Integer, nullable=False)
    x2 = db.Column(db.Integer, nullable=False)
    y2 = db.Column(db.Integer, nullable=False)
    temperatura_estimada = db.Column(db.Float, nullable=True)
    metodo_temperatura = db.Column(db.String(50), nullable=False, default="estimada_rgb_proxy")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "bird_uid": self.bird_uid,
            "confidence": round(self.confidence, 4),
            "bbox": [self.x1, self.y1, self.x2, self.y2],
            "temperatura_estimada": self.temperatura_estimada,
            "metodo_temperatura": self.metodo_temperatura,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class BirdIdentity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    bird_uid = db.Column(db.Integer, unique=True, nullable=False, index=True)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    sightings = db.Column(db.Integer, default=0, nullable=False)
    max_confidence = db.Column(db.Float, default=0.0, nullable=False)
    last_temp_estimada = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "bird_uid": self.bird_uid,
            "first_seen": self.first_seen.strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": self.last_seen.strftime("%Y-%m-%d %H:%M:%S"),
            "sightings": self.sightings,
            "max_confidence": round(self.max_confidence, 4),
            "last_temp_estimada": self.last_temp_estimada,
        }


class BirdTrackPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    bird_uid = db.Column(db.Integer, nullable=False, index=True)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "bird_uid": self.bird_uid,
            "x": self.x,
            "y": self.y,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class EventLog(db.Model, SyncMixin):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, default="info")
    message = db.Column(db.String(255), nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "event_type": self.event_type,
            "level": self.level,
            "message": self.message,
            "metadata": self.metadata_json,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class SensorReading(db.Model, SyncMixin):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    temperature_c = db.Column(db.Float, nullable=True)
    humidity_pct = db.Column(db.Float, nullable=True)
    ammonia_ppm = db.Column(db.Float, nullable=True)
    feed_level_pct = db.Column(db.Float, nullable=True)
    water_level_pct = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(50), nullable=False, default="sensor")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "ammonia_ppm": self.ammonia_ppm,
            "feed_level_pct": self.feed_level_pct,
            "water_level_pct": self.water_level_pct,
            "source": self.source,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    name = db.Column(db.String(80), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "name": self.name,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "active": self.active,
            "notes": self.notes,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class WeightEstimate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    avg_weight_g = db.Column(db.Float, nullable=False)
    ideal_weight_g = db.Column(db.Float, nullable=True)
    flock_count = db.Column(db.Integer, nullable=False, default=0)
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    source = db.Column(db.String(40), nullable=False, default="vision_estimate")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "avg_weight_g": self.avg_weight_g,
            "ideal_weight_g": self.ideal_weight_g,
            "flock_count": self.flock_count,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class AcousticReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    respiratory_health_index = db.Column(db.Float, nullable=False)
    cough_index = db.Column(db.Float, nullable=False)
    stress_audio_index = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(40), nullable=False, default="sensor")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "respiratory_health_index": self.respiratory_health_index,
            "cough_index": self.cough_index,
            "stress_audio_index": self.stress_audio_index,
            "source": self.source,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class ThermalAnomaly(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    bird_uid = db.Column(db.Integer, nullable=True, index=True)
    kind = db.Column(db.String(30), nullable=False)
    estimated_temp_c = db.Column(db.Float, nullable=False)
    ambient_temp_c = db.Column(db.Float, nullable=False)
    sector = db.Column(db.String(20), nullable=True)
    x = db.Column(db.Integer, nullable=True)
    y = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "bird_uid": self.bird_uid,
            "kind": self.kind,
            "estimated_temp_c": self.estimated_temp_c,
            "ambient_temp_c": self.ambient_temp_c,
            "sector": self.sector,
            "x": self.x,
            "y": self.y,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class EnergyUsageDaily(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    day = db.Column(db.DateTime, nullable=False, index=True)
    ventilacao_seconds = db.Column(db.Float, nullable=False, default=0.0)
    aquecedor_seconds = db.Column(db.Float, nullable=False, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "day": self.day.strftime("%Y-%m-%d"),
            "ventilacao_seconds": self.ventilacao_seconds,
            "aquecedor_seconds": self.aquecedor_seconds,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    actor = db.Column(db.String(80), nullable=False, default="system", index=True)
    action = db.Column(db.String(120), nullable=False, index=True)
    source = db.Column(db.String(30), nullable=False, default="backend")
    ip = db.Column(db.String(60), nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "actor": self.actor,
            "action": self.action,
            "source": self.source,
            "ip": self.ip,
            "details": self.details_json,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class SyncQueueItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    item_type = db.Column(db.String(60), nullable=False, index=True)
    payload_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    synced_at = db.Column(db.DateTime, nullable=True, index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "item_type": self.item_type,
            "payload": self.payload_json,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "synced_at": self.synced_at.strftime("%Y-%m-%d %H:%M:%S") if self.synced_at else None,
            "attempts": self.attempts,
        }


class BatchLogbook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    batch_id = db.Column(db.Integer, nullable=True, index=True)
    note = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(80), nullable=False, default="operador")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "batch_id": self.batch_id,
            "note": self.note,
            "author": self.author,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class PushToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "token": self.token,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    camera_id = db.Column(db.String(64), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    connection_type = db.Column(db.String(30), nullable=False, default="usb")
    connection_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="offline")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("tenant_id", "camera_id", name="uq_tenant_camera"),)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "camera_id": self.camera_id,
            "name": self.name,
            "connection_type": self.connection_type,
            "connection_url": self.connection_url,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class AutomationRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, default=1, index=True)
    name = db.Column(db.String(100), nullable=False)
    condition_variable = db.Column(db.String(50), nullable=False)  # Ex: 'temp_c', 'humidity_pct'
    condition_operator = db.Column(db.String(10), nullable=False)  # Ex: '>', '<', '=='
    condition_value = db.Column(db.Float, nullable=False)
    action_device = db.Column(db.String(50), nullable=False)  # Ex: 'exhaust_fan', 'heater'
    action_state = db.Column(db.String(20), nullable=False)  # Ex: 'on', 'off'
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "condition_variable": self.condition_variable,
            "condition_operator": self.condition_operator,
            "condition_value": self.condition_value,
            "action_device": self.action_device,
            "action_state": self.action_state,
            "active": self.active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
