---
name: store-specs
description: How to read, verify and update store limits (Fab, Unity Asset Store). Use when touching data/store_specs.json or validation.
---
# Store specs

- The single source of truth is `src/storelistingkit/data/store_specs.json`.
- Each store has `fields` (character limits: `max_chars`, optional `min_chars`, and `max_items` for lists)
  and `images` (slot id → `width`, `height`, `required`, `max_count`).
- Each store records `source` (where the numbers came from) and `last_checked` (a date).
- Before a release, a human checks every value against the live publisher guidelines and updates
  `last_checked`. Never change a limit only to make a test pass.
- Tests read limits from the file, so they never duplicate the numbers.
