# Wait, if I change `def video_feed():` to `async def video_feed():` in `backend/src/api/routes.py`,
# will it actually run?
# Maybe they are using an extension like `flask-async`? No, Flask 2+ supports async views out of the box if `asgiref` is installed!
# Wait! In Flask >2.0, if `asgiref` is installed, you CAN use `async def` for views!
# I proved earlier that `async def index():` and returning a `Response` works if it's a string.
# BUT what about `Response(generate())` where `generate` is an async generator?
# As we saw, `Response` does NOT support async generators.
# However, maybe the Flask response could just yield synchronously, or we can use a thread-safe wrapper.
