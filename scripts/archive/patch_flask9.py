# Wait! In `backend/main.py`:
# The route is defined as an async generator and returns StreamingResponse from FastAPI!
# Look at `backend/main.py` lines 286-308:
# async def generate():
#    ...
#    await asyncio.sleep(sleep_t)
# return StreamingResponse(generate(), ...)
#
# But in `backend/src/api/routes.py` line 128, the code uses `time.sleep()`.
# Wait, `backend/src/api/routes.py` is the OLD FLASK ROUTES.
# Why is there an issue opened against `backend/src/api/routes.py:128` "Using time.sleep in an asynchronous route handler blocks the event loop" ?
# Ah! Look closely at `backend/src/api/routes.py:128`. Is `video_feed` asynchronous?
# No, it's `def video_feed():`.
# But wait... does the problem mean that `cv_engine` or some other thread is blocked?
# Wait! What if `get_global_frame()` yields control?
# "Rationale: Using time.sleep in an asynchronous route handler blocks the event loop, reducing application throughput. Should use asyncio.sleep instead."
# If I just change `def video_feed` to `async def video_feed` and `def generate` to `async def generate`, it will throw a TypeError in Flask.
# Let's check `backend/src/api/routes.py` again. Maybe there's a typo in my understanding of the problem.
