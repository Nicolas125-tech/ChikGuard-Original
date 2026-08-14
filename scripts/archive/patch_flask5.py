from flask import Flask, Response, stream_with_context
import asyncio
import sys

app = Flask(__name__)

@app.route("/")
async def index():
    async def generate():
        for i in range(3):
            yield f"{i}\n"
            await asyncio.sleep(0.1)

    import asgiref.sync

    # Wait, maybe there's a workaround to stream async generators in Flask?
    # Another option: we use a sync generator, but it yields back, or we run asyncio.run()
    # inside the sleep. Wait, no, running asyncio.run inside sleep will start a new event loop.

    return "test"
