with open('backend/src/api/routes.py', 'r') as f:
    content = f.read()

# Make generate async and video_feed async
content = content.replace('def generate():', 'async def generate():')
content = content.replace('time.sleep(sleep_t)', 'await asyncio.sleep(sleep_t)')

import re
content = re.sub(r'def video_feed\(\):', r'async def video_feed():', content)

# But we know that Flask async generators do not work in Flask < 3? Or wait, Flask *does* support async generators?
# Let's check Flask version
import flask
print(flask.__version__)
