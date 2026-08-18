## 2026-08-09 - Add tests for FastAPI climate route
**What:** Added mocking for `aiohttp.ClientSession` to test `get_location_forecast`.
**Coverage:** Tested happy path for fetching location and weather data.
**Result:** Verified the route processes the external API responses correctly.
## 2026-08-09 - Add tests for FastAPI climate route
**What:** Added mocking for `aiohttp.ClientSession` to test `get_location_forecast`.
**Coverage:** Tested happy path for fetching location and weather data.
**Result:** Verified the route processes the external API responses correctly.

## 2024-05-30 - Unit Tests for TriZoneBehaviorAnalyzer
**Action:** Created `backend/tests/test_tri_zone_analyzer.py` to cover business rules related to animal welfare inside zones (Comfort, Cold Stress, Heat Stress) and window rolling states in `TriZoneBehaviorAnalyzer`.

## $(date +%Y-%m-%d) - [Add tests for BiometricWeightEstimator]
**Learning:** Implemented comprehensive unit tests for `BiometricWeightEstimator` in `backend/src/vision/weight_estimator.py` to target clamping extremes, boundary behaviors (like zero or negative ages, bounding boxes exceeding frame dimensions, and inverted coordinates) and fallback mechanisms (like empty detections and mixed species logic). By achieving 100% test coverage for this class, the tests ensure physical limits of biological weight (35g to 4500g) are strictly upheld.
**Action:** Added `backend/tests/test_weight_estimator.py`.
