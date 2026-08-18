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

## $(date +%Y-%m-%d) - Add missing tests for CameraTamperDetector
**Learning:** Added test suite for OpenCV-based camera tamper detection logic. The `CameraTamperDetector` utilizes counters tracking conditions (e.g., `_dark_counter`, `_freeze_counter`) which persist across frames to prevent sudden flapping. We must explicitly test that counter behavior decays properly when a normal frame is encountered after a sequence of anomalous ones.
**Action:** Created `tests/test_tamper_detector.py` exercising empty frames, normal frames, dark frames, blurry frames, and frozen frames alongside boundary tests to ensure temporal counters decrement and report correctly.
## $(date +%Y-%m-%d) - Add missing tests for CameraTamperDetector
**Learning:** Added test suite for OpenCV-based camera tamper detection logic. The `CameraTamperDetector` utilizes counters tracking conditions (e.g., `_dark_counter`, `_freeze_counter`) which persist across frames to prevent sudden flapping. We must explicitly test that counter behavior decays properly when a normal frame is encountered after a sequence of anomalous ones.
**Action:** Created `tests/test_tamper_detector.py` exercising empty frames, normal frames, dark frames, blurry frames, and frozen frames alongside boundary tests to ensure temporal counters decrement and report correctly.
