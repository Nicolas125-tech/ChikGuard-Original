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
