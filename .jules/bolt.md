## 2024-09-10 - O(N) filtering within render loop
**Learning:** In complex UI panels like `AdminPanel.jsx` that contain search and filtering logic, performing `Array.prototype.filter()` with multiple `.toLowerCase().includes()` comparisons on every component re-render creates a measurable CPU bottleneck, especially as the list size grows.
**Action:** Always wrap heavy list transformations (filtering, sorting) inside a `useMemo` hook with appropriate dependency arrays (`[list, search]`) to ensure the expensive O(N) operations only run when the underlying data actually changes, not on unrelated state updates.

## 2026-09-21 - Optimize Background Worker Sleep for Graceful Shutdown
**Learning:** Python's `time.sleep()` blocks the entire thread and delays signal handling or graceful shutdowns in long-running loops.
**Action:** Replace `time.sleep()` with `threading.Event().wait()` in continuous background tasks, and link the event to signal handlers (`SIGINT`, `SIGTERM`) to instantly interrupt the sleep and initiate teardown.
