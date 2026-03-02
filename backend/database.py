from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Tabela de Usuários (Login)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# NOVA TABELA: Histórico de Leituras
class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temperatura = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Data e hora automática

    def to_dict(self):
        return {
            "id": self.id,
            "temp": self.temperatura,
            "status": self.status,
            "hora": self.timestamp.strftime("%H:%M:%S"),
            "data": self.timestamp.strftime("%d/%m/%Y")
        }


class BirdSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
            "bird_uid": self.bird_uid,
            "confidence": round(self.confidence, 4),
            "bbox": [self.x1, self.y1, self.x2, self.y2],
            "temperatura_estimada": self.temperatura_estimada,
            "metodo_temperatura": self.metodo_temperatura,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }


class BirdIdentity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bird_uid = db.Column(db.Integer, unique=True, nullable=False, index=True)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    sightings = db.Column(db.Integer, default=0, nullable=False)
    max_confidence = db.Column(db.Float, default=0.0, nullable=False)
    last_temp_estimada = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "bird_uid": self.bird_uid,
            "first_seen": self.first_seen.strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": self.last_seen.strftime("%Y-%m-%d %H:%M:%S"),
            "sightings": self.sightings,
            "max_confidence": round(self.max_confidence, 4),
            "last_temp_estimada": self.last_temp_estimada,
        }


class BirdTrackPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bird_uid = db.Column(db.Integer, nullable=False, index=True)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "bird_uid": self.bird_uid,
            "x": self.x,
            "y": self.y,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class EventLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, default="info")
    message = db.Column(db.String(255), nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "event_type": self.event_type,
            "level": self.level,
            "message": self.message,
            "metadata": self.metadata_json,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }


class SensorReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    temperature_c = db.Column(db.Float, nullable=True)
    humidity_pct = db.Column(db.Float, nullable=True)
    ammonia_ppm = db.Column(db.Float, nullable=True)
    feed_level_pct = db.Column(db.Float, nullable=True)
    water_level_pct = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(50), nullable=False, default="simulated")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
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
    camera_id = db.Column(db.String(64), nullable=False, default="galpao-1", index=True)
    name = db.Column(db.String(80), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "name": self.name,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "active": self.active,
            "notes": self.notes,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
