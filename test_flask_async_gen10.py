import asyncio
from flask import Flask, Response

app = Flask(__name__)

@app.route("/")
async def index():
    # If the route is async, maybe it supports it?
    pass

# We already tested async def index() with Response(async_generator) and it failed.
