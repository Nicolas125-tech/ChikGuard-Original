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
