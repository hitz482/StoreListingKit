# Store Listing Kit

**Ship-ready Fab and Unity Asset Store listings from your plugin repo and real screenshots.**
A Windows app (installer or portable exe) with editor bridges for **Unreal Engine** and **Unity**.

Hack at FiftyFive: Build With AI Hackathon 2026.

```
repo / plugin folder ──► extracted profile (you edit) ──► screenshots ──► generate ──► review ──► export .zip
   zip · GitHub URL ·        every field shows                 real            Claude or      live limits    per store: listing.txt,
   UE/Unity editor           the file it came from             images only     offline draft  & warnings     listing.json, images at exact sizes
```

## Get it (Windows)

1. Download `StoreListingKit-Setup-x.y.z.exe` (per-user, no admin rights) or the portable `StoreListingKit.exe`
   from **Releases**, or from the **Actions → CI → StoreListingKit-windows** artifact.
2. Run it. Your browser opens the app.
3. Optional: **Connect engines → Install bridge** to add **Tools → Store Listing Kit** menus in Unreal Editor or Unity.

Full guide: [docs/WINDOWS.md](docs/WINDOWS.md).

## Run from source (any OS)

```bash
./scripts/setup.sh            # or .\scripts\setup.ps1 on Windows: venv, deps, tests
python -m storelistingkit     # opens the browser
python -m storelistingkit extract https://github.com/getnamo/UDP-Unreal   # profile as JSON
python -m storelistingkit selftest                                         # offline end-to-end check
```
Set `ANTHROPIC_API_KEY` for Claude-written copy (default model `claude-opus-5-5`, override with `SLK_MODEL`).
Without a key you get an offline draft built only from your repo's own text.

## What makes it trustworthy

- **Facts are extracted, not generated.** Engine adapters (`EngineAdapter` contract; Unreal and Unity)
  parse `.uplugin`, `*.Build.cs`, `package.json` and `.asmdef`. Every field records its source file,
  and you edit the profile *before* generation.
- **The model only writes copy.** Its output is a pydantic schema. Then come store limits and a
  **fact guard** (no platform, module or engine version outside the profile), a retry with feedback,
  and a hard failure. The technical-details section is rendered from the profile.
- **Repo text is untrusted.** Injection text such as "ignore previous instructions" is flagged, stripped
  from hidden carriers, bounded and fenced. See [SECURITY.md](SECURITY.md) (16 items, executed).
- **Real screenshots only.** They are composed into each store's exact sizes. Nothing is generated.

## Quality evidence

| | |
|---|---|
| Tests | 125+ (`pytest`): contract tests every adapter must pass, golden-file extractor tests, mocked-model integration tests, security tests, a full API journey |
| Evals | Extraction on **10 real MIT-licensed plugin repos** (4 UE, 6 Unity) pinned to commits: **100%** (baseline 97.9%, see [AI_LOG #10](AI_LOG.md)). [evals/results.md](evals/results.md) |
| CI | Lint, tests on Windows and Linux, evals (gate ≥95%), `pip-audit`, Windows exe + installer build, smoke test of both exes **and** the silently installed app |

### Eval results

<!-- copied from evals/results.md -->
| Case | Engine | Score |
|------|--------|-------|
| socketio-unreal | unreal | 100% |
| kawaiiphysics | unreal | 100% |
| tcp-unreal | unreal | 100% |
| udp-unreal | unreal | 100% |
| naughtyattributes | unity | 100% |
| native-gallery | unity | 100% |
| simple-file-browser | unity | 100% |
| ui-particle | unity | 100% |
| unitask | unity | 100% |
| toolbar-extender | unity | 100% |

## How it was built (AI development practices)

- **Spec first:** [PRD](docs/PRD.md) → [ARCHITECTURE](docs/ARCHITECTURE.md) → [TASKS](docs/TASKS.md) →
  code, with the prompt for each stage in [docs/prompts/](docs/prompts/).
- **Role-separated agents** ([.claude/agents/](.claude/agents/)): an *implementer*; a *test-writer* that
  sees only the spec and signatures; a read-only *reviewer* with its own
  [review-checklist skill](.claude/skills/review-checklist/SKILL.md).
- **Versioned context:** [CLAUDE.md](CLAUDE.md) and the skills evolve with `context:` commits that cite
  [AI_LOG](AI_LOG.md) entries.
- **Human gates:** uploads, network, auth and the API key path. See [docs/REVIEW_NOTES.md](docs/REVIEW_NOTES.md).
- **Decisions:** [docs/adr/](docs/adr/) (7 ADRs).

## Project layout

```
src/storelistingkit/   adapters/ (UE, Unity) · ingest · untrusted · generator · stores · images · exporter · server · engines · cli
src/storelistingkit/bridges/   Unreal plugin + Unity package (editor menus)
src/storelistingkit/static/    single-page UI (no build step)
src/storelistingkit/data/      store_specs.json · sample plugin for selftest
packaging/   PyInstaller spec · Inno Setup installer · icon
evals/       labelled real-repo cases · rubric · runner · results
tests/       pytest suite + fixtures + golden files
```

## Store limits

All limits live in [`store_specs.json`](src/storelistingkit/data/store_specs.json) (ADR 0005). They are marked
`verified: false` until re-checked against the live Fab and Unity publisher portals. Override them
without rebuilding via `SLK_STORE_SPECS=path\to\specs.json`.

License: MIT.
