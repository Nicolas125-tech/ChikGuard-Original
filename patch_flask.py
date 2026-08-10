import re

with open('backend/src/api/routes.py', 'r') as f:
    content = f.read()

# Make generate async
content = content.replace('def generate():', 'async def generate():')
# Replace time.sleep with await asyncio.sleep
content = content.replace('time.sleep(sleep_t)', 'await asyncio.sleep(sleep_t)')
# Make video_feed async
content = content.replace('def video_feed():', 'async def video_feed():')

with open('backend/src/api/routes.py', 'w') as f:
    f.write(content)
