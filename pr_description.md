🎯 **What:** Extracted several block-level dictionary builders from `get_summary` into smaller, independent helper functions (`_build_behavior_data`, `_build_sensors_data`, etc.).

💡 **Why:** `get_summary` was extremely long and primarily consisted of a massive dictionary assembly, which made it hard to read and modify. Breaking it up into domain-specific helpers improves maintainability and separation of concerns.

✅ **Verification:** Verified by running `python3 -m py_compile backend/src/api/system_api.py` and running the main test suite (`pytest tests/test_auth.py tests/test_fastapi_accounts.py` subset checked since no dedicated system_api tests exist) to ensure no regressions occurred.

✨ **Result:** A more concise, readable `get_summary` function with isolated logic for each data subset.
