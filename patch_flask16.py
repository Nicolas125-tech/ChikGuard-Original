# Wait, if test_routes passes with `async def video_feed()`, then that means the tests don't actually test hitting the /api/video endpoint, or they don't care that it returns an async generator?
# Let's check `backend/tests/test_routes.py`
