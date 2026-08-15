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

## 2024-10-25 - Improve async action loading states and prevent double-submission
**Learning:** Found an accessibility and UX issue pattern where buttons executing asynchronous actions (like submitting forms or deleting items) lacked visual feedback during the action and remained clickable. This could lead to duplicate API calls and user confusion about whether their action was registered.
**Action:** When implementing asynchronous actions attached to buttons (e.g., in forms or lists), use local state to track the loading status (e.g., `isSaving` or `deletingId`). Update the button to display a loading spinner (like `RefreshCw` with `animate-spin`), disable the button (`disabled={loadingState}`), and use standard `disabled:opacity-50 disabled:cursor-not-allowed` styles to provide immediate, clear feedback and prevent duplicate submissions.

## 2024-11-20 - Ensure htmlFor properly matches IDs for screen readers in AdminPanel.jsx
**Learning:** Found an accessibility issue where inputs in AdminPanel.jsx lacked proper htmlFor ID linkages, meaning screen readers couldn't correctly associate labels with forms.
**Action:** Always add unique `id` elements to `<input>`, `<select>`, and `<textarea>` elements, and correctly reference them with `htmlFor` in the respective `<label>` elements.
## 2024-05-18 - Fix Voltar button in LoginScreen
**Learning:** The "Voltar" element was a div with a click handler which violates semantic accessibility rules and causes issues for keyboard users.
**Action:** Replace actionable divs with native `<button>` elements, include an `aria-label`, and use `focus-visible:ring-*` classes for clear keyboard navigation cues.
