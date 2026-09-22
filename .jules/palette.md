## 2023-10-27 - Decorative SVGs and aria-hidden
**Learning:** Screen readers announce SVGs as generic images if they lack an accessible name. For purely decorative icons (like the ones in AlertsPanel.jsx), this creates unnecessary noise for screen reader users. However, adding `aria-label` to buttons that already have visible text overrides the visible text, breaking WCAG 2.5.3 (Label in Name) and confusing voice-control users.
**Action:** Always add `aria-hidden="true"` to decorative `<svg>` elements used as icons to prevent redundant screen reader announcements. Never add `aria-label` to buttons that already have visible text.
## 2024-05-18 - Add keyboard focus states to sidebar navigation
**Learning:** Found that core sidebar navigation tabs lacked explicit keyboard focus states (`focus-visible`). This makes keyboard navigation almost invisible on darker themes.
**Action:** Always add explicit `focus-visible:ring` utilities to global navigation elements (like sidebars and navbars) as they are the primary way keyboard users traverse the application.

## 2024-05-18 - [Adição de focus-visible para navegação por teclado]
**Learning:** Elementos de UI como botões e inputs sem o atributo `focus-visible` do Tailwind (ou equivalentes de CSS) podem inviabilizar o uso do site por usuários de teclado devido a falta de feedback visual sobre onde estão localizados ao tabularem. Adicionalmente, quando não há aria-label em botões ou ícones o usuário de tela fica confuso. Além disso, usar `element.focus()` no Playwright pode causar Timeouts (como em `input_locator.focus()`) ou não disparar o estilo de foco visual. A maneira mais natural e garantida de capturar `focus-visible` em screenshots é simular a navegação pressionando Tab via `page.keyboard.press("Tab")`.
**Action:** Na proxima vez aplicarei proativamente estilos globais de foco usando `focus-visible` em painéis de inputs, botoes e usarei a tecla tab para testes end-to-end (e2e).
## 2024-05-19 - Adding aria-label to Icon-Only Buttons
**Learning:** Found that some buttons with only icons (e.g., the fullscreen button in CameraPanel) were lacking an `aria-label`. Without this, screen readers cannot announce the button's purpose, making the UI inaccessible to visually impaired users.
**Action:** When adding or encountering icon-only buttons, ensure they have a descriptive `aria-label` attribute (like `aria-label="Alternar Tela Cheia"`).
