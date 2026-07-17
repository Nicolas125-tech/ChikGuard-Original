## 2025-07-10 - Explicit Labels for Simulator Inputs
**Learning:** Using purely `<label>Text</label><input />` adjacent to each other breaks screen reader association and click-to-focus functionality in inputs.
**Action:** Always link `<label>` and `<input>` using the `htmlFor` and `id` properties. Use correct `step` properties for number inputs accepting decimals.
## 2025-07-10 - Screen Reader Labels for SmartOpsPanel
**Learning:** Inputs that lack visible textual labels (like logbook entry or batch management) should use `sr-only` class `<label>` elements linked to the `id` of the input to ensure screen readers correctly associate the label and the input field. Relying solely on `aria-label` might not be enough or is inferior to explicit linked labels.
**Action:** Always link `<label>` with `htmlFor` matching the `<input id>`, using `.sr-only` class to hide the label visually if the design does not afford space for a textual label.
