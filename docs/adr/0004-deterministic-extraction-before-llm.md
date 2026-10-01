# ADR 0004: Deterministic extraction first; the LLM only writes copy

Status: accepted, 2026-10-01

## Context
LLMs asked to "read the repo" invent module names, engine versions and platforms.

## Decision
Engine adapters parse `.uplugin`, `*.Build.cs`, `package.json` and `.asmdef` deterministically.
The user edits the resulting profile. The model gets the profile and writes marketing copy only.
The technical-details section of each listing is rendered from the profile. A fact guard rejects
copy that names a module or platform the profile does not contain.

## Consequences
+ Extraction is unit-testable with golden files and measurable by the eval harness.
− Repos with unusual layouts extract less. The user fixes that in the edit step.
