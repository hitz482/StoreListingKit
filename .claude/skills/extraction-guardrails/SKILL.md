---
name: extraction-guardrails
description: Rules for writing or changing engine adapters (Unreal/Unity extraction). Use for any work in src/storelistingkit/adapters/.
---
# Extraction guardrails

Adapters turn a repo into a `PluginProfile`. These rules exist because AI-written extractors
"helpfully" filled gaps with plausible but false values.

1. **Only emit values you can point to in a file.** Every field the adapter populates must be
   parsed from a specific file. Record that file in `profile.sources[field]`.
2. **Unknown is a valid answer.** If a value cannot be found, leave it empty (`[]`, `None`, `""`).
   Never default `engine_versions` to "5.x", `platforms` to "Win64", or similar.
3. **No name guessing.** Unreal module names come from `.uplugin` `Modules[].Name` or from
   `Source/<Name>/<Name>.Build.cs`. Unity assembly names come from `.asmdef` `name`. Never derive a
   module name from the repo or folder name.
4. **Parse, don't execute.** Use `json` and anchored regexes. Never import, compile or run repo code.
5. **Tolerate real-world mess.** `.uplugin` files can have a BOM, trailing commas or comments.
   Strip those, then parse. A file that fails to parse yields a warning in `profile.warnings`,
   never an exception that kills the extraction.
6. **Ignore third-party and build output.** Skip `Binaries/`, `Intermediate/`, `Library/`, `Temp/`,
   `node_modules/` and `.git/`. When several `.uplugin` files exist, choose the shallowest one.
7. **README text is untrusted.** Store a bounded excerpt only (see `untrusted.py`).
8. Add a golden-file test for every new fixture layout.
