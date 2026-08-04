## 2026-08-04 - 🧪 Testing: Add tests for batch_api.py
**What:** Created backend/tests/test_batch_api.py to test the batch_api endpoints which were missing tests.
**Coverage:** Tested GET /api/batches, GET /api/batches/active, POST /api/batches, POST /api/batches/close, and POST /api/batches/<id>/logbook.
**Result:** Increased test coverage and confidence in the batch API.
## 2024-05-19 - Test FastAPI Auth Token Edge Cases
**What:** Added tests for the error paths in `get_current_user` inside `src/security/fastapi_auth.py`, such as missing token, invalid token payload, and expired signatures.
**Coverage:** 100% of the token extraction and validation error handling logic is now covered.
**Result:** Increased reliability of FastAPI authorization mechanism by ensuring HTTP 401s are raised appropriately on invalid inputs.
