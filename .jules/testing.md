## 2026-08-04 - 🧪 Testing: Add tests for batch_api.py
**What:** Created backend/tests/test_batch_api.py to test the batch_api endpoints which were missing tests.
**Coverage:** Tested GET /api/batches, GET /api/batches/active, POST /api/batches, POST /api/batches/close, and POST /api/batches/<id>/logbook.
**Result:** Increased test coverage and confidence in the batch API.
## 2024-08-04 - Improve predict_slaughter_date testing coverage
**What:** The `predict_slaughter_date` function lacked comprehensive tests, particularly around biological monotonicity (birds don't lose weight) and target weight behaviors. Addressed by adding two test scenarios targeting these behaviors to complement existing path coverage. Also removed duplicated/unused tests.
**Coverage:** Ensured behavior coverage of polynomial regression outputs where expected weight decreases and scenarios where the predicted weight has already met the target weight. Total branch/statement coverage stands at 100%.
**Result:** Higher reliability for the biological growth prediction logic.
