# ADR 0003: Compose real screenshots; do not generate images

Status: accepted, 2026-10-01

## Context
Stores and buyers penalise misleading imagery. Generated "gameplay" images misrepresent a plugin.

## Decision
`images.py` contain-fits each real screenshot into the exact pixel size of each store slot. The
padding is a blurred, darkened copy of the same screenshot, with an optional caption band. No pixels
are invented beyond background and layout.

## Consequences
+ Output is honest and deterministic, so it can be golden-tested by size and mode.
− Visual flair is limited. That is the trade-off the scope cuts chose.
