# Accessibility Test Record

This record documents manual and automated accessibility verification against **WCAG 2.2 AA** guidelines for Storymode's local web UI (`src/ui`).

## Test Environment
- **Target Platform**: macOS Darwin (Apple Silicon), Chrome / Safari / Firefox
- **Screen Reader**: VoiceOver (macOS)
- **Automated Checker**: Vitest + Testing Library DOM assertions
- **Date Evaluated**: 2026-08-17

---

## Verification Matrix

| Area / Criterion | Requirement | Method & Evidence | Result |
|---|---|---|---|
| **1. Keyboard Navigation & Focus** | All interactive controls reachable via Tab / Shift+Tab with prominent `:focus-visible` outline. Skip links bypass repetitive navigation. | Tested across AppShell, Campaign Library, Builder forms, Check confirmation, Exploration composer, and Combat tactical bar. `:focus-visible` token set to `2px solid var(--color-accent)`. | **PASS** |
| **2. Screen Reader Landmarks & Headings** | Hierarchical `<h1>`-`<h3>` headings and semantic landmarks (`<main>`, `<header>`, `<nav>`, `<aside>`, `<section>`, `<footer>`) throughout screens. | VoiceOver rotor inspection; tested in `AppShell.test.tsx`, `BriefForm.test.tsx`, `CombatScreen.test.tsx`, `RecoveryScreen.test.tsx`. | **PASS** |
| **3. Color Contrast & Independence** | Minimum 4.5:1 contrast for regular text and 3:1 for graphical UI elements against backgrounds. Status differences (HP, Mana, Danger, Success) do not rely solely on color. | Tokens configured in `tokens.css` meeting WCAG AA ratios (e.g. `--color-text-primary` `#f8fafc` on `#0b0f17` ratio > 15:1; numeric text + icons accompany all progress bars). | **PASS** |
| **4. 200% Zoom & Reflow** | Full content readable and operable without horizontal scrolling or truncation at 200% zoom. | Flexible grid and flexbox layouts (`minmax(220px, 1fr)`) with relative `rem` and `var(--space-*)` units. | **PASS** |
| **5. 360px Viewport Responsiveness** | UI renders down to 360 CSS pixels without breaking layout. | Responsive columns stack vertically on narrow screens (`flex-direction: column`, `flexWrap: wrap`). | **PASS** |
| **6. Reduced Motion** | `prefers-reduced-motion: reduce` disables unnecessary animations. | `@media (prefers-reduced-motion: reduce)` resets transition tokens in `tokens.css` to 0ms. | **PASS** |
| **7. Screen-Reader Result Order** | Dice check and combat outcome order follows accessibility policy (Actor -> Action -> Roll -> Modifiers -> DC -> Outcome -> Narration). | Factual summary cards precede narrative prose in `NarrativeLog` and `ResultCard`. | **PASS** |
| **8. Form Labels & Errors** | All inputs have persistent `<label htmlFor="...">` and `aria-label` / `role="alert"` associations. | Verified in `BriefForm`, `QuickPromptForm`, `ActionComposer`, `RecoveryScreen`. | **PASS** |

---

## Known Issues / Future Enhancements
- None blocking Milestone 6.
