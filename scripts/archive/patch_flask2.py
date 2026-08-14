import re

with open('backend/src/api/routes.py', 'r') as f:
    content = f.read()

replacement = """
                    # Sleep adaptativo: dorme apenas o tempo restante
                    elapsed = time.perf_counter() - t0
                    sleep_t = stream_interval - elapsed
                    if sleep_t > 0.001:
                        # Yield context back to event loop or sleep
                        # Wait, since this is a synchronous generator running inside
                        # a threadpool via ensure_sync, if we use asyncio.run or similar
                        # it might block the thread but yield to other asyncio tasks
                        # Actually, wait, maybe we should just make the route use asyncio
                        pass
"""
# Let's check how the FastAPI version did it
