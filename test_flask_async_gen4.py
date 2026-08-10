from flask import Flask, Response
import asyncio

app = Flask(__name__)

@app.route("/")
def index():
    async def generate():
        for i in range(3):
            yield f"{i}\n"
            await asyncio.sleep(0.1)

    import asgiref.sync
    # We can try to use async_to_sync on a generator, but that's not how it works.

    # Actually, asgiref.sync.async_to_sync doesn't work on async generators.
    # We would need to run the loop in a separate thread.
    return "ok"

if __name__ == "__main__":
    print("Just a test")
