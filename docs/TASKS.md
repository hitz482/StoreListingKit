# Task breakdown

Stage 3 of the spec-first loop. Prompt: [prompts/03-tasks.md](prompts/03-tasks.md).
Each task names the agent role that owns it (see [CLAUDE.md](../CLAUDE.md#agent-roles)).

| # | Task | Owner | Gate | Status |
|---|------|-------|------|--------|
| T1 | Pydantic models (`PluginProfile`, `StoreCopy`, `ListingKit`) | implementer | reviewer | done |
| T2 | `EngineAdapter` contract and contract tests (written from the spec only) | test-writer | reviewer | done |
| T3 | Unreal adapter, plus golden-file tests | implementer | reviewer | done |
| T4 | Unity adapter, plus golden-file tests | implementer | reviewer | done |
| T5 | Safe ingestion: zip-bomb, traversal, symlink, size and count limits; GitHub URL allow-list | implementer | **human** | done |
| T6 | Untrusted-content handling (prompt injection) | implementer | **human** | done |
| T7 | Store specs and validation | implementer | reviewer | done |
| T8 | Claude generator: schema, retry, hard failure, fact guard; mocked-model tests | implementer + test-writer | reviewer | done |
| T9 | Offline template generator | implementer | reviewer | done |
| T10 | Screenshot composition to exact store sizes | implementer | reviewer | done |
| T11 | Export zip | implementer | reviewer | done |
| T12 | HTTP API: session token, rate limit, job runner with partial results | implementer | **human** | done |
| T13 | Single-page UI: the six-step journey, empty/loading/error states | implementer | human (UX pass) | done |
| T14 | CLI and `selftest` | implementer | reviewer | done |
| T15 | PyInstaller Windows build and CI (lint, tests, evals, exe smoke test) | implementer | reviewer | done |
| T16 | Eval harness on labelled public repos, with a results table | implementer | human (labels) | done |
| T19 | Windows installer (Inno Setup, per-user) and CI install test | implementer | reviewer | done |
| T20 | Engine detection and UE/Unity editor bridges (AI_LOG #4) | implementer | human (R5) + manual editor QA | done (editor QA todo) |
| T17 | Dogfooding run and demo before/after | human | — | todo |
| T18 | Demo slide (pain, audience, measured saving) | human | — | todo |

**Human gates** mark code that was never accepted unreviewed: anything that touches uploads,
network fetches, the API key path or auth. Review notes for those gates go in
[REVIEW_NOTES.md](REVIEW_NOTES.md).
