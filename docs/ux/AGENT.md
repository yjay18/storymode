# UX Agent Rules

- Read the governing game-design and API/schema contract before editing a screen.
- Render allowed actions and numbers from server results; do not duplicate mechanics.
- Keep keyboard, focus, text alternatives, contrast, motion, and live announcements
  correct in the same change, with component tests.
- Never render model/imported text as raw HTML.
- Mutations use stable command IDs across transport retries and show uncertain commit
  status safely; never issue a new roll command merely because a response timed out.
- Update screen-state documentation and test loading/error/empty/success branches.
