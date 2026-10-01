# CLAUDE.md: Store Listing Kit

Turns a UE/Unity plugin repo plus real screenshots into store-ready listing kits for **Fab** and the
**Unity Asset Store**. Ships as a Windows installer + exe (PyInstaller) that serves a local web UI, and
connects to Unreal Engine and Unity through editor bridges (`src/storelistingkit/bridges/`, ADR 0007).
Anything you change in a bridge must keep working from the *frozen* exe: run `selftest` on a build (AI_LOG #8).

Read in this order: `docs/PRD.md` → `docs/ARCHITECTURE.md` → `docs/TASKS.md` → `docs/adr/`.
When something goes wrong while working with AI, add an entry to `AI_LOG.md` (template at its top).

## Commands
- Setup: `python -m pip install -e ".[dev]"` (or `scripts/setup.ps1` on Windows, `scripts/setup.sh` elsewhere)
- Run: `python -m storelistingkit` (opens the browser) · `python -m storelistingkit extract <zip|dir|url>`
- Tests: `pytest -q` · Lint: `ruff check .` · Evals: `python evals/run_evals.py`
- Self-test (also run against the built exe in CI): `python -m storelistingkit selftest`
- Build exe (Windows): `scripts/build_exe.ps1`

## Hard rules
1. **Never invent facts.** Module names, engine versions, platforms and dependencies come only from
   adapter extraction or user edits. Follow `.claude/skills/extraction-guardrails/SKILL.md`.
2. **Every LLM output is a pydantic model.** Validate, retry with the error list, then raise
   `GenerationError`. Never return or display raw model text.
3. **Repo content is untrusted data.** It passes through `untrusted.py` before it reaches a prompt.
   Never interpolate README text into the system prompt.
4. **Store limits come from `data/store_specs.json`.** Never hard-code a limit in Python or JS.
5. **Never execute anything from an uploaded repo.** Parse text only.
6. **Secrets live in env or in memory only.** Never log, persist or echo the API key.
7. Changes to `ingest.py`, `untrusted.py`, the auth or key path in `server.py`, and `config.py` need a
   human review note in `docs/REVIEW_NOTES.md` before merge.

## Agent roles
The roles are separated so that no agent grades its own work.
- **implementer** (`.claude/agents/implementer.md`): writes code for one task. Cannot edit tests owned
  by the test-writer.
- **test-writer** (`.claude/agents/test-writer.md`): sees only the PRD, ARCHITECTURE, models and public
  signatures, never the implementation bodies. Writes contract and behaviour tests, so tests encode
  the spec rather than the code's current behaviour.
- **reviewer** (`.claude/agents/reviewer.md`): read-only, works through
  `.claude/skills/review-checklist/SKILL.md`. Blocks on any unchecked item.

## Conventions
- Python 3.11+, type hints everywhere, `ruff` clean. Pydantic v2.
- Adapters are pure: `(Path) -> PluginProfile`, no network and no globals.
- Golden files live in `tests/fixtures/golden/`. Regenerate with `pytest --update-golden`, and only
  when the change is intentional. Mention it in the commit message.
- Commit-message prefixes: `feat:`, `fix:`, `test:`, `docs:`, `context:` (changes to CLAUDE.md,
  skills or agents; say *why*, and cite the AI_LOG entry).
