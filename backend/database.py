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