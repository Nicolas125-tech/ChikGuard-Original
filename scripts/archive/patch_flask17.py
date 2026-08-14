# Look, there is no test for `/api/video` at all in `test_routes.py`!
# And wait! If I change `def video_feed():` to `async def video_feed():`, the route will be broken when accessed in Flask, because it returns a regular Response with an async generator, which raises TypeError.
# Wait. I should just use `asyncio.sleep` but block?
# NO, the rationale is: "Using time.sleep in an asynchronous route handler blocks the event loop, reducing application throughput. Should use asyncio.sleep instead."
# If `video_feed` is NOT an asynchronous route handler (it's `def` not `async def`), then why does the issue say it IS?
# Let's check `backend/main.py`. It has an `async def video_feed()` route.
# Look at `backend/main.py` lines 248-308:
"""
async def video_feed(token: str = None):
    # ...
    async def generate():
        import cv2
        from src.core.state import get_global_frame
        import asyncio
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        stream_interval = 1.0 / 30
        try:
            while True:
                t0 = time.perf_counter()
                frame = get_global_frame()
                if frame is not None:
                    ret, buf = cv2.imencode(".jpg", frame, encode_params)
                    if ret:
                        yield (b"--frame\r\n"
                               b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
                elapsed = time.perf_counter() - t0
                sleep_t = stream_interval - elapsed
                if sleep_t > 0.001:
                    await asyncio.sleep(sleep_t)
        except GeneratorExit:
            pass
    return StreamingResponse(...)
"""
# So `main.py` ALREADY has `await asyncio.sleep(sleep_t)`!
# The task specifically points to `backend/src/api/routes.py:128`.
# Does `backend/src/api/routes.py` use an async route handler? No.
# If I just change it to async, it breaks Flask.
