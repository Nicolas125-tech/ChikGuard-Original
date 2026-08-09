## 2025-07-10 - Explicit Labels for Simulator Inputs
**Learning:** Using purely `<label>Text</label><input />` adjacent to each other breaks screen reader association and click-to-focus functionality in inputs.
**Action:** Always link `<label>` and `<input>` using the `htmlFor` and `id` properties. Use correct `step` properties for number inputs accepting decimals.
