# ADR 0005: Store limits live in a data file, not in code

Status: accepted, 2026-10-01

## Context
Store requirements (character limits, image sizes) change, and the authors could not check every
value against the live seller portals while building.

## Decision
`src/storelistingkit/data/store_specs.json` holds every limit, with a `source` note and a
`last_checked` field per store. Validation and image composition read only from this file. A user
can override it with `SLK_STORE_SPECS=/path/to/specs.json`, with no rebuild needed.

## Consequences
+ Fixing a wrong limit is a one-line data change.
− The shipped values must be re-verified against the Fab and Unity publisher guidelines before each
  release (this is on the release checklist).
