🎯 **What:** Optimized the `/api/alerts` endpoint in `backend/app.py`. Filtered out `NORMAL` readings directly in the database query instead of iterating through all results in Python. Replaced string concatenation for sorting with raw datetime object comparisons.

💡 **Why:** Filtering at the database level significantly reduces memory consumption and execution time when there are many `NORMAL` readings, resolving an N+1 style inefficiency. Furthermore, building a string (`f"{x['data']} {x['hora']}"`) to use as a sorting key is much slower than utilizing raw datetime objects which carry chronological accuracy intrinsically.

✅ **Verification:** Ran backend tests to verify functionality remains stable. Checked endpoints response logic visually via Python AST format updates. Confirmed with standard tests `pytest tests/`.

✨ **Result:** A more responsive and scalable API endpoint under load, better utilization of the database query planner, and cleaner handling of datetimes for sorting.
