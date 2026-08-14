from flask import Flask, Response, stream_with_context
import asyncio

app = Flask(__name__)

@app.route("/")
def index():
    async def generate():
        for i in range(3):
            yield f"{i}\n"
            await asyncio.sleep(0.1)

    # In Flask > 2.0, if you have an async generator, you can return it directly? No, Response takes an iterable.
    # What if we just return the async generator?
    # return generate() ? No, need headers.
    try:
        return Response(stream_with_context(generate()), mimetype="text/plain")
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    with app.test_client() as client:
        try:
            resp = client.get("/")
            print(resp.data)
        except Exception as e:
            print("ERROR:", type(e), e)
