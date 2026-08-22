1. **Fix Table Row Loading UX Bug in `AdminPanel.jsx`**
   - Use `python3 modify_admin_panel.py` to change `actionLoading` from a single string to use a specific identifier string.
   - We need to scope `actionLoading` to both the `userId` and the specific action, e.g., `${userId}-approve`.
   - Update `handleApprove`, `handleReject`, `handleSuspend`, `handleReactivate` to set `actionLoading` to `${userId}-<action>`.
   - Update `UserRow` to accept these changes and check against specific actions (e.g., `actionLoading === '${u.id}-approve'`).

2. **Frontend Verification**
   - Run `cd frontend && pnpm lint` and ensure there are no errors related to my changes. Note that there are already some linting errors in the codebase, I should only fix those related to my change.
   - Run frontend tests.

3. **Pre-commit Instructions**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
