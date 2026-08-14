# If the task says "time.sleep in an asynchronous route handler blocks the event loop",
# but it's clearly a Flask synchronous view.
# Maybe the author of the task mistakenly thought it was an async route?
# Or wait! If `time.sleep` blocks the worker thread (e.g. gunicorn with gevent or asyncio worker),
# then standard `asyncio.sleep` won't work unless it's `async def`.
# Wait, look at `backend/src/api/routes.py` lines 106-130:
# ```python
#         def generate():
#             last_t = time.perf_counter()
#             try:
#                 while True:
#                     t0 = time.perf_counter()
#                     frame = get_global_frame()
#                     # ...
#                     elapsed = time.perf_counter() - t0
#                     sleep_t = stream_interval - elapsed
#                     if sleep_t > 0.001:
#                         time.sleep(sleep_t)
# ```
# If this route is actually running via an ASGI adapter, like in `main.py`:
# `socket_app.other_asgi_app = fastapi_app` (this doesn't include Flask app anymore)
# But `backend/main.py` DOES include it? Wait, where is `app_flask_legacy` used?
# In `backend/app_flask_legacy.py`:
# ```python
# app.register_blueprint(create_api_blueprint(api_deps))
# ```
# In `backend/scripts/start.sh` or something?
# Let's check `backend/scripts/` or `backend/tests/` to see how it's executed.
