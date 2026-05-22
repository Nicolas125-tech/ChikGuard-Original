🎯 **What:** Removed the unused `datetime` import from `backend/src/reports/generator.py`. Also cleaned up an unused `database.db` import and applied standard formatting using `autopep8` to resolve some long lines.

💡 **Why:** `datetime` and `db` were imported but not used in the file, causing unnecessary mental overhead and violating clean code guidelines. Removing unused code improves code readability and maintainability.

✅ **Verification:** Verified by checking that no references to the `datetime` object existed in the file (only `timedelta`). Ran `flake8` to ensure there were no other linting issues. Ran backend tests with `pytest` to ensure no regressions.

✨ **Result:** Cleaner code that is easier to maintain with no unused imports.
