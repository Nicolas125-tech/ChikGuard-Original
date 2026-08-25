import time
from app_flask_legacy import app, db, BirdSnapshot, BirdIdentity, _utcnow

def setup(start_uid, n):
    rows = []
    for u in range(start_uid, start_uid + n):
        rows.append(
            BirdSnapshot(
                bird_uid=u,
                confidence=0.9,
                x1=0, y1=0, x2=10, y2=10,
                temperatura_estimada=30.0,
                metodo_temperatura="est",
            )
        )
    return rows

def original_method(rows):
    now_dt = _utcnow()
    with app.app_context():
        bird_uids = [r.bird_uid for r in rows]
        existing = BirdIdentity.query.filter(BirdIdentity.bird_uid.in_(bird_uids)).all()
        id_map = {idx.bird_uid: idx for idx in existing}

        for row in rows:
            identity = id_map.get(row.bird_uid)
            if identity is None:
                identity = BirdIdentity(
                    bird_uid=row.bird_uid,
                    first_seen=now_dt,
                    last_seen=now_dt,
                    sightings=1,
                    max_confidence=row.confidence,
                    last_temp_estimada=row.temperatura_estimada,
                )
                db.session.add(identity)
                id_map[row.bird_uid] = identity
            else:
                identity.last_seen = now_dt
                identity.sightings = int(identity.sightings) + 1
                if row.confidence > float(identity.max_confidence):
                    identity.max_confidence = row.confidence
                identity.last_temp_estimada = row.temperatura_estimada
        db.session.commit()


def optimized_method(rows):
    now_dt = _utcnow()
    with app.app_context():
        bird_uids = [r.bird_uid for r in rows]
        existing = BirdIdentity.query.filter(BirdIdentity.bird_uid.in_(bird_uids)).all()
        id_map = {idx.bird_uid: idx for idx in existing}

        for row in rows:
            identity = id_map.get(row.bird_uid)
            if identity is None:
                identity = BirdIdentity(
                    bird_uid=row.bird_uid,
                    first_seen=now_dt,
                    last_seen=now_dt,
                    sightings=1,
                    max_confidence=row.confidence,
                    last_temp_estimada=row.temperatura_estimada,
                )
                db.session.add(identity)
            else:
                identity.last_seen = now_dt
                identity.sightings = int(identity.sightings) + 1
                if row.confidence > float(identity.max_confidence):
                    identity.max_confidence = row.confidence
                identity.last_temp_estimada = row.temperatura_estimada
        db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    # First run: inserts
    rows_orig = setup(1000, 100)
    t0 = time.time()
    original_method(rows_orig)
    t1 = time.time()

    rows_opt = setup(2000, 100)
    t2 = time.time()
    optimized_method(rows_opt)
    t3 = time.time()

    print("--- INSERT ---")
    print(f"Original: {t1-t0:.4f}s")
    print(f"Optimized: {t3-t2:.4f}s")

    # Second run: updates (identities already exist)
    t4 = time.time()
    original_method(rows_orig)
    t5 = time.time()

    t6 = time.time()
    optimized_method(rows_opt)
    t7 = time.time()

    print("--- UPDATE ---")
    print(f"Original: {t5-t4:.4f}s")
    print(f"Optimized: {t7-t6:.4f}s")
