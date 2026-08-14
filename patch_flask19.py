# The instruction: "Using time.sleep in an asynchronous route handler blocks the event loop, reducing application throughput. Should use asyncio.sleep instead."
# If I make `video_feed` an `async def`, and I want to return a generator:
# Flask > 2.0 streaming with async generators requires `flask.stream_with_context` or something?
# No, Flask docs say: "If you want to stream data from an async view, you should use an async generator."
# Wait, Flask 3.0 added support for async generators in Response!
# Let's test Flask 3.1.3 (which is installed) with an async generator!
