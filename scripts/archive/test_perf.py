import time
import os
import sys

# Set environment variables for auth module
os.environ['SUPABASE_JWT_SECRET'] = 'dummy_secret_dummy_secret_dummy_secret_for_testing_32b'
os.environ['ADMIN_PASSWORD'] = 'testpassword'

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from flask import Flask
from database import db, Reading
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    # Insert some dummy data
    for i in range(100):
        status = "NORMAL"
        if i % 10 == 0:
            status = "ALERTA"
        r = Reading(
            temperatura=25.0 + i % 5,
            status=status,
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        db.session.add(r)
    db.session.commit()

    # Define the old function
    def old_get_temperature_summary(Reading):
        ultima = Reading.query.order_by(Reading.id.desc()).first()
        recentes = Reading.query.order_by(Reading.id.desc()).limit(30).all()
        temperaturas = [item.temperatura for item in recentes]
        alertas = [item for item in recentes if item.status != "NORMAL"]
        return {
            "temperatura_atual": ultima.temperatura if ultima else 0,
            "status_atual": ultima.status if ultima else "INICIANDO",
            "media_temperatura": (
                round(sum(temperaturas) / len(temperaturas), 1) if temperaturas else 0
            ),
            "total_alertas": len(alertas),
        }

    # Define the new function
    def new_get_temperature_summary(Reading):
        recentes = Reading.query.order_by(Reading.id.desc()).limit(30).all()
        ultima = recentes[0] if recentes else None

        temperaturas = [item.temperatura for item in recentes]
        alertas = [item for item in recentes if item.status != "NORMAL"]

        return {
            "temperatura_atual": ultima.temperatura if ultima else 0,
            "status_atual": ultima.status if ultima else "INICIANDO",
            "media_temperatura": (
                round(sum(temperaturas) / len(temperaturas), 1) if temperaturas else 0
            ),
            "total_alertas": len(alertas),
        }

    # Measure old
    start = time.perf_counter()
    for _ in range(1000):
        old_res = old_get_temperature_summary(Reading)
    duration_old = time.perf_counter() - start
    print(f"Old approach (1000 iterations): {duration_old:.4f} seconds")

    # Measure new
    start = time.perf_counter()
    for _ in range(1000):
        new_res = new_get_temperature_summary(Reading)
    duration_new = time.perf_counter() - start
    print(f"New approach (1000 iterations): {duration_new:.4f} seconds")

    print(f"Match: {old_res == new_res}")
