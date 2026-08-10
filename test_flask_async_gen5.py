from flask import Flask, Response
import asyncio

app = Flask(__name__)

@app.route("/")
async def index():
    async def generate():
        for i in range(3):
            yield f"{i}\n"
            await asyncio.sleep(0.1)

    import asgiref.sync
    # Convert async generator to sync generator so Response can iterate it
    # We can create a sync wrapper manually

    def sync_gen():
        ag = generate()
        loop = asyncio.new_event_loop()
        try:
            while True:
                yield loop.run_until_complete(ag.__anext__())
        except StopAsyncIteration:
            pass
        finally:
            loop.close()

    return Response(sync_gen(), mimetype="text/plain")

if __name__ == "__main__":
    with app.test_client() as client:
        try:
            resp = client.get("/")
            print(resp.data)
        except Exception as e:
            import traceback
            traceback.print_exc()
