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

## 2024-05-18 - Decorative Icons in Action Buttons
**Learning:** Found an accessibility issue where action buttons containing SVG icons (like `RefreshCw` or `Download`) alongside text were reading out confusingly to screen readers or adding unnecessary noise because the icons lacked `aria-hidden="true"`.
**Action:** Always add `aria-hidden="true"` to decorative or supplementary icons inside buttons that already have descriptive text, and ensure the button itself has `focus-visible` utility classes for clear keyboard navigation cues.

## 2024-11-20 - Shared Table Row Loading UX Bug
**Learning:** Using a single `actionLoading = userId` state for a table row with multiple distinct actions (Approve, Suspend, Delete) causes all buttons in that row to show a loading spinner simultaneously when any one action is triggered. This creates a confusing UX where the user isn't sure which action is actually processing.
**Action:** Always scope loading states to both the unique entity ID *and* the specific action being performed (e.g., `actionLoading = '${userId}-approve'`) when a row contains multiple interactive elements.
## 2025-08-23 - Decorative Icons in Table Actions
**Learning:** Supplementary Lucide icons inside action buttons and table header tabs are often missed for accessibility if they don't include `aria-hidden="true"`, causing unnecessary screen reader noise.
**Action:** Add `aria-hidden="true"` to supplementary icons across standard action UI elements to ensure clean screen reader output.
## 2025-02-23 - Dynamic ARIA Labels in Lists
**Learning:** Generic `aria-label`s like "Editar câmera" and "Excluir câmera" inside repeated table rows or lists are confusing for screen reader users because they lack context about *which* item is being targeted.
**Action:** Always include a unique identifier (like the item's name or title) in the `aria-label` for action buttons within loops (e.g., `aria-label={\`Editar câmera ${cam.name}\`}`).
## 2024-05-24 - Accessibility Enhancements in CameraPanel

**Learning:** When turning a pair of buttons into a segmented control, they need to act as a cohesive unit for screen readers. Using `role="group"` and `aria-pressed` makes the context clear. Also, decorative icons within these buttons must be hidden using `aria-hidden="true"` to avoid redundant announcements.
**Action:** Always add `role="group"` and `aria-label` to the container of segmented controls, and explicitly manage `aria-pressed` states on the child buttons. Mask decorative icons.
## 2025-08-28 - Explicit Labels for Standalone Inputs and Proper ARIA Labels
**Learning:** Found an accessibility issue where inputs like search or calculators lacked proper `htmlFor` ID linkages, and many action buttons lacked `aria-label`s. Also discovered a loading state issue where all actions in a table row showed a spinner when only one was clicked.
**Action:** Always add unique `id` elements to inputs and reference them with `htmlFor` in `sr-only` labels if visually hidden. Ensure all icon buttons or state-toggling buttons have descriptive `aria-label`s. Ensure loading state (`isAnyActioning`) is scoped specifically to the user ID and action via string splitting or exact matching.
## 2024-05-19 - Segmented Controls in React
**Learning:** Found a group of toggle buttons functioning as segmented controls wrapped in a standard div without an explicit grouping role. While `aria-pressed` was correctly handling the state, screen readers could not determine the buttons were part of a related set.
**Action:** Always wrap segmented toggle buttons in a container with `role="group"` and provide a descriptive `aria-label` to provide context to assistive technologies.
