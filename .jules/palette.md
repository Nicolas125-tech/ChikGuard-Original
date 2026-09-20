## 2023-10-27 - Decorative SVGs and aria-hidden
**Learning:** Screen readers announce SVGs as generic images if they lack an accessible name. For purely decorative icons (like the ones in AlertsPanel.jsx), this creates unnecessary noise for screen reader users. However, adding `aria-label` to buttons that already have visible text overrides the visible text, breaking WCAG 2.5.3 (Label in Name) and confusing voice-control users.
**Action:** Always add `aria-hidden="true"` to decorative `<svg>` elements used as icons to prevent redundant screen reader announcements. Never add `aria-label` to buttons that already have visible text.
## 2024-05-18 - Add keyboard focus states to sidebar navigation
**Learning:** Found that core sidebar navigation tabs lacked explicit keyboard focus states (`focus-visible`). This makes keyboard navigation almost invisible on darker themes.
**Action:** Always add explicit `focus-visible:ring` utilities to global navigation elements (like sidebars and navbars) as they are the primary way keyboard users traverse the application.
