## 2024-05-29 - Missing accessibility labels on form elements without explicit labels
**Learning:** In complex interface components, such as inline management tools or administrative tables, `<input>` and `<select>` elements are often implemented dynamically without adjacent `<label>` tags to save space or follow a minimalist design pattern. This causes severe accessibility issues as screen readers cannot interpret the purpose of these fields. I discovered this specific pattern in `SmartOpsPanel.jsx` (batch creation and logbook entries), `ManagementPanel.jsx` (audio upload), and `AdminPanel.jsx` (inline role `<select>`).
**Action:** When creating or refactoring minimalist inline forms or list-item controls where visual labels are omitted, always ensure `aria-label` or `aria-labelledby` attributes are explicitly added to `<input>`, `<select>`, and `<textarea>` elements to maintain screen reader compatibility without compromising the visual layout.

## 2026-05-29 - Missing keyboard focus states (focus-visible)
**Learning:** The application lacked global `:focus-visible` styles, making keyboard navigation (tabbing) impossible for accessibility users since they couldn't see which element was focused. Relying entirely on Tailwind's default reset or missing hover states breaks WCAG compliance for interactive elements.
**Action:** Add a robust, global `*:focus-visible` outline in `index.css` that inherits the brand color (e.g. emerald-400). This provides an instant accessibility win across all components without needing to add `focus:` classes to every single button manually.

## 2026-05-29 - Missing feedback on async form submissions
**Learning:** In panels with async operations (like `SmartOpsPanel`), buttons lacked loading/disabled states during API calls. This allows impatient users to click multiple times, potentially creating duplicate database entries (like creating multiple batches simultaneously).
**Action:** Always wrap `fetch` calls in `try/finally` blocks, introducing `isLoading` state variables. Disable both the button and its associated input fields while loading, and replace the button text with a loading spinner to provide immediate visual feedback.

## 2026-05-29 - Boring Empty States decrease engagement
**Learning:** In the `CamerasManager`, when there were no cameras, the table simply showed a tiny text row saying "Nenhuma câmera conectada". This is a missed opportunity. Empty states should not just inform, they should guide the user to action.
**Action:** Replace plain text empty states with rich, centered UI components containing a relevant icon (with low opacity), an explanatory text of *why* it's empty, and a clear Call-To-Action (CTA) button to create the first item. This significantly reduces friction for onboarding new users.

## 2026-05-29 - Poor visual feedback with "..." text on buttons
**Learning:** In the `AdminPanel`, loading states for sensitive actions (Approve, Suspend, Delete) simply replaced the button text with "...". This feels broken or unresponsive, especially if the API takes more than a second, leading to anxiety during destructive actions.
**Action:** Always use an animated SVG spinner (e.g., `<RefreshCw className="animate-spin" />`) alongside clear progressive text (e.g., "Aprovando...", "Excluindo...") to assure the user that the background process is running smoothly.
## 2024-06-02 - Prefer aria-pressed for Toggle Buttons with Text
**Learning:** While dynamic `aria-label`s (e.g., "Ativar X" / "Desativar X") provide clear actionable instructions, they override the visible internal text of a button for screen readers. For toggle buttons that contain descriptive visible text, a more strictly correct pattern is to use `aria-pressed="true|false"`. This preserves the internal description while accurately announcing the button's state to assistive technology.
**Action:** Default to `aria-pressed` for stateful toggle buttons that have visible text inside them. Reserve dynamic `aria-label`s for icon-only toggle buttons or buttons where the internal text is non-descriptive.
## 2024-06-13 - Interactive Divs Must Support Keyboard Navigation
**Learning:** Custom interactive components, such as the large statistics cards in `OverviewPanel.jsx` that function as navigation tabs (`onClick`), often lack keyboard support. While they look and act like buttons to mouse users, keyboard-only users cannot focus them or activate them.
**Action:** When applying `onClick` and `role="button"` to non-semantic elements like `div`s, always pair them with `tabIndex={0}`, an `onKeyDown` handler (listening for `Enter` and `Space`), and visible focus states (e.g., `focus-visible:ring-2`) to ensure WCAG compliance.
