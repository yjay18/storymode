# Accessibility

Target WCAG 2.2 AA for the local web UI.

## Required practices

- All functionality is keyboard usable with visible focus and logical DOM/tab order.
- Use semantic headings, landmarks, buttons, forms, tables, dialogs, and lists before
  ARIA. Every field has a persistent label and error association.
- Contrast meets AA. HP/armour/mana, status, opportunity, and result differences use
  text/icons in addition to color.
- Provide skip links to narrative, actions, and current turn. Restore focus after
  dialogs, route changes, check results, and combat transitions.
- Announce concise committed results through a polite live region; do not announce
  streaming model tokens. Critical errors use assertive announcement sparingly.
- Respect `prefers-reduced-motion`; dice/transition animations are optional and can be
  disabled. Never delay result access for animation.
- Area art and portraits have concise contextual alternatives. Decorative generated
  texture has empty alt. The deterministic fallback carries equivalent labels.
- Narrative text supports zoom/reflow, adjustable line length/font size, and does not
  place essential text inside images.
- Timeouts are model/transport concerns, not user response deadlines. No timed choice
  expires because of wall-clock time.

## Screen-reader result order

For a check: action -> die -> named modifiers -> total -> DC -> outcome -> confirmed
effects -> optional narration. For combat: actor -> chosen skill/targets -> mana ->
base effects -> optional effect die/bonus -> defeats/status -> next actor.

## Testing

Each interactive component gets keyboard/focus assertions and automated axe checks
when the UI test stack is added. Manually test at least keyboard-only, VoiceOver on
macOS, 200% zoom, 360 px reflow, reduced motion, and high-contrast/color-independent
states before each UI milestone is complete.
