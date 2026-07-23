## 2025-07-10 - Explicit Labels for Simulator Inputs
**Learning:** Using purely `<label>Text</label><input />` adjacent to each other breaks screen reader association and click-to-focus functionality in inputs.
**Action:** Always link `<label>` and `<input>` using the `htmlFor` and `id` properties. Use correct `step` properties for number inputs accepting decimals.
## 2025-07-10 - Screen Reader Labels for SmartOpsPanel
**Learning:** Inputs that lack visible textual labels (like logbook entry or batch management) should use `sr-only` class `<label>` elements linked to the `id` of the input to ensure screen readers correctly associate the label and the input field. Relying solely on `aria-label` might not be enough or is inferior to explicit linked labels.
**Action:** Always link `<label>` with `htmlFor` matching the `<input id>`, using `.sr-only` class to hide the label visually if the design does not afford space for a textual label.
## 2025-07-21 - Explicit Labels for Forms and Range Inputs
**Learning:** Using `aria-label` alone for inputs like file uploads (`type="file"`) and range sliders (`type="range"`) can be insufficient or poorly supported by screen readers, particularly if the component relies on native browser form controls.
**Action:** Always link `<label>` with `htmlFor` matching the `<input id>`, using `.sr-only` class to hide the label visually for standalone inputs like ranges or specific hidden file uploads (e.g. manual audio classification).

## 2024-07-23 - Shared Table Row Loading UX Bug
**Learning:** Using a single `actionLoading = userId` state for a table row with multiple distinct actions (Approve, Suspend, Delete) causes all buttons in that row to show a loading spinner simultaneously when any one action is triggered. This creates a confusing UX where the user isn't sure which action is actually processing.
**Action:** Always scope loading states to both the unique entity ID *and* the specific action being performed (e.g., `actionLoading = '${userId}-approve'`) when a row contains multiple interactive elements.
