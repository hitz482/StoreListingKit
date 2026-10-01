# PRD: Store Listing Kit

Status: v1 (October 2026, Hack at FiftyFive "Build With AI" hackathon)
Stage 1 of the spec-first loop: PRD → [ARCHITECTURE](ARCHITECTURE.md) → [TASKS](TASKS.md) → implementation.
Prompt used to draft this document: [prompts/01-prd.md](prompts/01-prd.md).

## Problem

Developers who sell Unreal Engine plugins on **Fab** or Unity packages on the **Unity Asset Store**
spend hours on each listing. They copy facts out of the repo by hand (engine versions, modules,
platforms), rewrite the README into marketing copy, and resize screenshots to each store's image
specs. The work is repetitive, and the facts often end up wrong: a listing claims a platform or a
module the plugin doesn't ship.

## Users

- Solo and small-studio sellers on Fab and the Unity Asset Store.
- Studios that ship internal plugins and need consistent listings across many products.

## Goal

Get from a plugin repo plus real screenshots to a **store-ready listing kit** in minutes, not hours.
Every fact in the kit is traceable to the repo, and the kit fits each store's limits.

## The journey (one flawless path)

1. **Connect the repo**: upload a `.zip`, or paste a public GitHub URL.
2. **Review the extracted profile**: the engine adapter extracts name, version, engine versions,
   modules, platforms, dependencies and README highlights. The user corrects anything wrong
   *before* generation (human in the loop).
3. **Upload screenshots**: real screenshots are the source of truth. No generated gameplay imagery.
4. **Generate**: Claude writes per-store copy (title, short description, long description,
   feature bullets, tags). Progress and partial results show per store.
5. **Review and edit**: live character counters and store-constraint warnings.
6. **Export**: a zip with one folder per store. Each holds the copy as `.txt` and `.json` plus
   images composed to that store's exact pixel dimensions.

## Functional requirements

| ID | Requirement |
|----|-------------|
| F1 | Accept a zip upload (size-limited and checked for zip bombs and path traversal) or a public GitHub URL. |
| F2 | Detect the engine (Unreal or Unity) through an `EngineAdapter` contract, and extract a typed `PluginProfile`. |
| F3 | Let the user edit every profile field before generation. |
| F4 | Accept up to 20 screenshots (PNG/JPEG/WebP), validated and size-limited. |
| F5 | Generate per-store copy through Claude, with schema-validated output, a retry on invalid output and a hard failure path. Raw model text never reaches the UI. |
| F6 | Offer an offline (template) generator when no API key is configured, clearly labelled as a draft. |
| F7 | Validate against each store's limits (character counts, image dimensions, counts) and show warnings. |
| F8 | Export a zip in store-ready formats. |
| F9 | Ship as a Windows `.exe` that needs no Python install, and also run as `python -m storelistingkit`. |
| F10 | Install on Windows via a per-user installer (no admin rights) with Start-menu shortcuts and an uninstaller. |
| F11 | Connect to Unreal Engine and Unity: detect local engine installs; install an editor bridge into a project that adds **Tools → Store Listing Kit** menus to open the tool on the project's plugin and capture listing screenshots. |
| F12 | Accept a local plugin folder as a source (used by the bridges and by the UI). |

## Non-functional requirements

- **Facts are never invented.** Module names, engine versions and platforms in the output must come
  from the profile. Technical-details sections are rendered from the profile, not written by the model.
- **Repo content is untrusted.** A README may contain prompt-injection text. See [SECURITY.md](../SECURITY.md).
- **Local-first.** The server binds to `127.0.0.1` only and requires a per-launch session token.
- **Secrets stay in env** (`ANTHROPIC_API_KEY`). A key entered in the UI lives in memory only.

## Out of scope (scope cuts)

User accounts beyond simple auth, team features, multiple LLM providers, image generation beyond
backgrounds and layout, Steam/itch.io/mobile stores, GitHub OAuth for private repos.

## Success metrics

- The eval harness ([evals/](../evals/)) scores extraction accuracy of 90% or higher on labelled public repos.
- Measured time from opening the tool to an exported kit is under 10 minutes, against a manual
  baseline of roughly 2 to 4 hours per listing (see [BUSINESS.md](BUSINESS.md) for how this is measured).
