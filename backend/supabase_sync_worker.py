import asyncio
import json
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import time

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: Supabase credentials not found in environment. Sync will be mocked.")
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class SupabaseSyncWorker:
    def __init__(self, log_file="tracking_logs.json", batch_size=50, interval_seconds=5):
        self.log_file = log_file
        self.batch_size = batch_size
        self.interval_seconds = interval_seconds
        self.last_processed_idx = 0

    async def fetch_new_logs(self):
        """Reads new log entries from the JSON file since the last read."""
        if not os.path.exists(self.log_file):
            return []

        try:
            with open(self.log_file, "r") as f:
                # Assuming the tracking script writes a JSON array.
                # In a real streaming scenario, JSON lines (.jsonl) would be better.
                data = json.load(f)
                
            new_logs = data[self.last_processed_idx:]
            self.last_processed_idx = len(data)
            return new_logs
        except json.JSONDecodeError:
            # File might be mid-write
            return []
        except Exception as e:
            print(f"Error reading logs: {e}")
            return []

    def transform_for_supabase(self, logs):
        """Transforms tracking logs into a flat format for Supabase insertion."""
        records = []
        for frame_log in logs:
            timestamp = frame_log.get("timestamp", time.time())
            frame_num = frame_log.get("frame")
            
            for det in frame_log.get("detections", []):
                records.append({
                    "track_id": det["id"],
                    "class_id": det["class"],
                    "confidence": det["confidence"],
                    "pos_x": det["smoothed_centroid"][0],
                    "pos_y": det["smoothed_centroid"][1],
                    "frame_number": frame_num,
                    # Convert UNIX timestamp to ISO format for Postgres
                    "detected_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                })
        return records

    async def batch_upsert(self, records):
        """Sends records to Supabase in batches."""
        if not records:
            return

        print(f"Preparing to sync {len(records)} records to Supabase...")
        
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]
            
            if supabase:
                try:
                    # Assuming table name is 'bird_tracking_logs'
                    # Upsert based on track_id and detected_at (assuming these form a unique constraint if needed)
                    response = supabase.table("bird_tracking_logs").insert(batch).execute()
                    print(f"Synced batch of {len(batch)} records.")
                except Exception as e:
                    print(f"Supabase sync error: {e}")
            else:
                print(f"[Mock Sync] Synced batch of {len(batch)} records to Supabase.")
            
            # Small yield to event loop
            await asyncio.sleep(0.1)

    async def run(self):
        print("Starting Supabase Sync Worker...")
        print(f"Listening for logs in {self.log_file} every {self.interval_seconds} seconds.")
        
        while True:
            new_logs = await self.fetch_new_logs()
            if new_logs:
                records = self.transform_for_supabase(new_logs)
                await self.batch_upsert(records)
            else:
                pass # No new logs
                
            await asyncio.sleep(self.interval_seconds)

if __name__ == "__main__":
    worker = SupabaseSyncWorker(log_file="tracking_logs.json", batch_size=100, interval_seconds=5)
    
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("Sync Worker stopped by user.")
