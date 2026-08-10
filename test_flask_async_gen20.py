import asyncio
from flask import Flask, Response

app = Flask(__name__)

@app.route("/")
async def index():
    async def generate():
        for i in range(3):
            yield f"{i}\n"
            await asyncio.sleep(0.1)

    # Flask 3+ allows this?
    return generate(), {"Content-Type": "text/plain"}

if __name__ == "__main__":
    with app.test_client() as client:
        try:
            resp = client.get("/")
            print(resp.data)
        except Exception as e:
            print("ERROR:", type(e), e)
