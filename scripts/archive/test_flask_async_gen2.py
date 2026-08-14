from flask import Flask, Response
import asyncio
import asgiref.sync

app = Flask(__name__)

@app.route("/")
def index():
    async def generate():
        for i in range(3):
            yield f"{i}\n"
            await asyncio.sleep(0.1)

    # In a synchronous route in Flask, you can't easily return an async generator directly
    # for Response. The Response object iterates over the generator synchronously.
    # What happens if we return an async generator?
    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    with app.test_client() as client:
        try:
            resp = client.get("/")
            print(resp.data)
        except Exception as e:
            print("ERROR:", type(e), e)
