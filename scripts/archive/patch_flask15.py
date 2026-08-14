import re

with open('backend/src/api/routes.py', 'r') as f:
    content = f.read()

# Let's change `def video_feed():` to `async def video_feed():`
# And `def generate():` to `async def generate():`
# And `time.sleep(sleep_t)` to `await asyncio.sleep(sleep_t)`
content = re.sub(r'def video_feed\(\):', r'async def video_feed():', content)
content = re.sub(r'def generate\(\):', r'async def generate():', content)
content = content.replace('time.sleep(sleep_t)', 'await asyncio.sleep(sleep_t)')

# Let's see if we can use a wrapper for the async generator so Flask doesn't crash?
# Wait! In Flask, you CAN return an async generator if you use quart or if there's an async monkeypatch.
# Wait, maybe they use asgiref's async_to_sync?
# If we test this change, does `test_routes.py` still pass?
with open('backend/src/api/routes.py', 'w') as f:
    f.write(content)
