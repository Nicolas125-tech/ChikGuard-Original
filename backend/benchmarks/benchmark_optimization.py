import time
import sqlite3
import json

# Simulated constants
ACTIVE_CAMERA_ID = "galpao-1"

def _safe_json(value):
    return json.dumps(value)

class MockSyncQueueItem:
    def __init__(self, item_type, payload_json, status="pending"):
        self.item_type = item_type
        self.payload_json = payload_json
        self.status = status

def benchmark_original(anomalies_count=30):
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE thermal_anomaly (id INTEGER PRIMARY KEY, camera_id TEXT, bird_uid INTEGER, kind TEXT, estimated_temp_c REAL, ambient_temp_c REAL, sector TEXT, x INTEGER, y INTEGER)')
    cursor.execute('CREATE TABLE sync_queue_item (id INTEGER PRIMARY KEY, item_type TEXT, payload_json TEXT, status TEXT)')

    anomalies = [{"bird_uid": i, "kind": "fever", "estimated_temp_c": 39.5, "ambient_temp_c": 30.0, "sector": "A1", "x": 100, "y": 100} for i in range(anomalies_count)]

    start_time = time.time()

    # Simulate the original logic
    # with app.app_context():
    # rows = [ThermalAnomaly(camera_id=ACTIVE_CAMERA_ID, **a) for a in anomalies[:30]]
    # db.session.bulk_save_objects(rows)
    # db.session.commit()
    cursor.executemany('INSERT INTO thermal_anomaly (camera_id, bird_uid, kind, estimated_temp_c, ambient_temp_c, sector, x, y) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       [(ACTIVE_CAMERA_ID, a['bird_uid'], a['kind'], a['estimated_temp_c'], a['ambient_temp_c'], a['sector'], a['x'], a['y']) for a in anomalies])
    conn.commit()

    # for row in rows:
    #     _enqueue_sync_item("thermal_anomaly", row.to_dict())
    for i in range(len(anomalies)):
        # _enqueue_sync_item
        # with app.app_context():
        # db.session.add(SyncQueueItem(...))
        # db.session.commit()
        cursor.execute('INSERT INTO sync_queue_item (item_type, payload_json, status) VALUES (?, ?, ?)',
                       ("thermal_anomaly", _safe_json(anomalies[i]), "pending"))
        conn.commit() # This is the N+1 problem

    end_time = time.time()
    conn.close()
    return end_time - start_time

def benchmark_optimized(anomalies_count=30):
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE thermal_anomaly (id INTEGER PRIMARY KEY, camera_id TEXT, bird_uid INTEGER, kind TEXT, estimated_temp_c REAL, ambient_temp_c REAL, sector TEXT, x INTEGER, y INTEGER)')
    cursor.execute('CREATE TABLE sync_queue_item (id INTEGER PRIMARY KEY, item_type TEXT, payload_json TEXT, status TEXT)')

    anomalies = [{"bird_uid": i, "kind": "fever", "estimated_temp_c": 39.5, "ambient_temp_c": 30.0, "sector": "A1", "x": 100, "y": 100} for i in range(anomalies_count)]

    start_time = time.time()

    # Simulate the optimized logic
    cursor.executemany('INSERT INTO thermal_anomaly (camera_id, bird_uid, kind, estimated_temp_c, ambient_temp_c, sector, x, y) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       [(ACTIVE_CAMERA_ID, a['bird_uid'], a['kind'], a['estimated_temp_c'], a['ambient_temp_c'], a['sector'], a['x'], a['y']) for a in anomalies])

    # Collect sync items
    sync_items = [("thermal_anomaly", _safe_json(a), "pending") for a in anomalies]
    cursor.executemany('INSERT INTO sync_queue_item (item_type, payload_json, status) VALUES (?, ?, ?)', sync_items)

    conn.commit() # Single commit

    end_time = time.time()
    conn.close()
    return end_time - start_time

if __name__ == "__main__":
    count = 30
    print(f"Running benchmark with {count} anomalies...")

    original_time = 0
    optimized_time = 0
    iterations = 100

    for _ in range(iterations):
        original_time += benchmark_original(count)
        optimized_time += benchmark_optimized(count)

    avg_original = original_time / iterations
    avg_optimized = optimized_time / iterations

    print(f"Original average time: {avg_original:.6f}s")
    print(f"Optimized average time: {avg_optimized:.6f}s")
    print(f"Improvement: {(avg_original - avg_optimized) / avg_original * 100:.2f}%")
