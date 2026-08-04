PR Title: 🧹 Code Health: Remove unused `annotations` import in `enhanced_detector.py`

PR Description:
🎯 **What:** Removed the unused `from __future__ import annotations` import at line 34 in `backend/src/vision/enhanced_detector.py`.
💡 **Why:** Static analysis (and visual inspection) confirmed that this import was not being referenced anywhere else in the file. Since the project uses Python 3.12 (where type hints are natively robust without it unless strictly needed for unresolved string references) and it was not actually utilized, removing it improves the maintainability and readability of the codebase by eliminating dead code.
✅ **Verification:** Verified that the file compiled successfully (`py_compile`), ran tests utilizing this module (`backend/tests/test_enhanced_detector.py`) to confirm no functionality or runtime inference behaviour was broken, and used `ruff` to ensure clean formatting.
✨ **Result:** A cleaner `enhanced_detector.py` file with dead code successfully eliminated, matching codebase standards without impacting system behavior.
