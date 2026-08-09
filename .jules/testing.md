## 2023-10-20 - Add error path tests for report generation
**What:** Created error path tests for `generate_weekly_report` and `generate_esg_report` functions in `backend/src/reports/generator.py` to ensure exception propagation on database failures.
**Coverage:** 2 new error paths in `src.reports.generator`
**Result:** Increased coverage and safety nets against silent database failures during report generation.
