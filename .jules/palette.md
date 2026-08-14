## 2025-07-10 - Explicit Labels for Simulator Inputs
**Learning:** Using purely `<label>Text</label><input />` adjacent to each other breaks screen reader association and click-to-focus functionality in inputs.
**Action:** Always link `<label>` and `<input>` using the `htmlFor` and `id` properties. Use correct `step` properties for number inputs accepting decimals.
## 2024-11-20 - Ensure htmlFor properly matches IDs for screen readers in AdminPanel.jsx
**Learning:** Found an accessibility issue where inputs in AdminPanel.jsx lacked proper htmlFor ID linkages, meaning screen readers couldn't correctly associate labels with forms.
**Action:** Always add unique `id` elements to `<input>`, `<select>`, and `<textarea>` elements, and correctly reference them with `htmlFor` in the respective `<label>` elements.
