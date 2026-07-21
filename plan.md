1. **Fix missing labels and `id` references in forms for Screen Reader accessibility.**
   - In `frontend/src/components/ManagementPanel.jsx`, update the "Classificação Manual (.wav)" input to add an explicitly linked label using `htmlFor` and `id`, maintaining the `.sr-only` class to hide it visually.

2. **Pre-commit Steps**
   - Run tests, check formats, and fix lint issues via `pnpm` before finalizing.
