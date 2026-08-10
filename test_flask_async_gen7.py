from flask import Flask, Response
import asyncio
import time

app = Flask(__name__)

@app.route("/")
def index():
    def generate():
        for i in range(3):
            yield f"{i}\n"
            # How does one sleep without blocking the main event loop
            # if we are in gevent? Wait, is the app using gevent?
            pass
    return Response(generate(), mimetype="text/plain")
