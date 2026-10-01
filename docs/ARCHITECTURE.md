# Architecture

Stage 2 of the spec-first loop. Prompt: [prompts/02-architecture.md](prompts/02-architecture.md).

```
                ┌───────────────────── StoreListingKit.exe (PyInstaller) ─────────────────────┐
 Browser  ◄────►│ server.py (FastAPI, 127.0.0.1, session token, rate limit)                   │
 (static UI)    │   │                                                                         │
                │   ├─ ingest.py ──── safe zip extraction / GitHub codeload download          │
                │   ├─ adapters/ ──── EngineAdapter ─┬─ UnrealAdapter (.uplugin, *.Build.cs)  │
                │   │                                └─ UnityAdapter  (package.json, .asmdef) │
                │   │                     ▼                                                   │
                │   │               PluginProfile (pydantic) ◄── user edits                   │
                │   ├─ generator.py ─ ClaudeGenerator (schema + retry + hard fail)            │
                │   │                 TemplateGenerator (offline, deterministic)              │
                │   │                     ▼                                                   │
                │   │               StoreCopy per store ──► stores.py (limits, validation)   │
                │   ├─ images.py ──── compose real screenshots → store image slots            │
                │   └─ exporter.py ── zip: <store>/listing.txt, listing.json, images/*.png    │
                └─────────────────────────────────────────────────────────────────────────────┘
```

## Modules

| Module | Responsibility | Deterministic? |
|--------|----------------|----------------|
| `models.py` | Pydantic schemas: `PluginProfile`, `StoreCopy`, `ListingKit`, `ValidationIssue`. The contract between all layers. | yes |
| `adapters/base.py` | `EngineAdapter` ABC: `detect(root) -> float` confidence, `extract(root) -> PluginProfile`. | yes |
| `adapters/unreal.py` | Reads `*.uplugin` (JSON), `Source/*/*.Build.cs`, `Config/FilterPlugin.ini`, README. | yes |
| `adapters/unity.py` | Reads UPM `package.json`, `*.asmdef`, `ProjectSettings/ProjectVersion.txt`, README. | yes |
| `ingest.py` | Zip and URL ingestion with all upload protections. | yes |
| `untrusted.py` | Treats repo text as data: truncates it, flags injection patterns, wraps it in delimiters. | yes |
| `stores.py` | Loads `data/store_specs.json`; validates copy and images against it. | yes |
| `generator.py` | `ListingGenerator` protocol. `ClaudeGenerator` calls Claude with structured output, re-validates, retries with feedback, then fails hard. `TemplateGenerator` is the offline fallback. | Claude: no |
| `images.py` | Pillow composition: contain-fit the screenshot over a blurred copy of itself, optional caption band, exact output size. | yes |
| `exporter.py` | Builds the export zip. | yes |
| `server.py` | HTTP API and job runner (background thread per generation, polled for partial results). | — |
| `engines.py` | Detect local UE installs (Epic launcher manifest, registry) and Unity Hub editors; install editor bridges into projects; write `%LOCALAPPDATA%/StoreListingKit/location.json` so bridges can find the exe. | yes |
| `bridges/` | **Unreal:** content-only plugin with `Content/Python/init_unreal.py` that adds Tools-menu entries (open the tool on a project plugin; `HighResShot` screenshot capture). **Unity:** an editor-only UPM package with `[MenuItem]`s (open the tool on the selected package; `ScreenCapture` from the Game view). Both launch `StoreListingKit.exe --source <plugin> --screenshots <dir>`. | — |
| `cli.py` | `serve` (default, opens the browser), `extract`, `selftest`. | — |

## Windows distribution

```
CI (windows-latest) ── PyInstaller ──► dist/StoreListingKit/ (folder) ── Inno Setup ──► StoreListingKit-Setup-x.y.z.exe
                     └─ PyInstaller ──► dist/StoreListingKit.exe (portable single file)
Both exes and the silently-installed copy run `selftest` in CI before artifacts are published.
```
The installer is per-user (`%LOCALAPPDATA%\Programs\StoreListingKit`), writes `HKCU\Software\StoreListingKit\InstallPath`,
and ships the bridges under `EditorBridges\` for manual copying.

## Data flow and trust boundaries

1. **Untrusted input**: the zip or URL, its file contents, the screenshots.
2. `ingest.py` makes it safe to touch: limits, path checks, and image decode via Pillow with
   `MAX_IMAGE_PIXELS`.
3. Adapters parse **structured** files (JSON, C# build rules) with regexes and `json`. No code from
   the repo is ever executed.
4. The **profile** is the only thing the model sees, plus a truncated README excerpt wrapped in
   `<untrusted_repo_content>` tags. The system prompt says to treat that excerpt as data.
5. Model output → `StoreCopy` pydantic validation → store-limit validation → fact guard (no module or
   platform names outside the profile). If any step fails, the generator retries with the error list.
   After `max_attempts` it raises `GenerationError`, and the UI shows a clean error.
6. Technical details (modules, engine versions, platforms) are **rendered from the profile**, never
   written by the model.

## Key decisions

See [adr/](adr/). In short: a local web UI packaged as an exe (0001); Claude Opus 5.5 with structured
output (0002); screenshot composition over image generation (0003); deterministic extraction
before the LLM (0004); the store specs as a data file (0005); a session token instead of accounts (0006);
editor bridges instead of a native engine plugin (0007).
