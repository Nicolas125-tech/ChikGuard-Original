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
## 2024-08-18 - Added BiometricWeightEstimator Tests
**Component:** `backend/src/vision/weight_estimator.py`
**Coverage:**
- Young chicks vs adult hens age/growth baseline estimations
- Confidence adjustments with and without instance segmentation masks
- Min/max biological limits
- Array aggregations on flock weight estimation including edge cases of no valid bird detections
**Result:** Enhanced test coverage ensures reliability of the non-invasive computer vision weight estimation regression logic.
