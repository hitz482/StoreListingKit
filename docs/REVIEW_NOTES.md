# Human review notes (validation gates)

Code in these areas is never accepted unreviewed (CLAUDE.md rule 7). Each note records what was
checked line by line, by whom and when, and the outcome.

| ID | Area | Reviewed | Outcome |
|----|------|----------|---------|
| R1 | `ingest.py` (zip/URL/folder) | 2026-10-01, author + Claude (reviewer role) | Checked the order of checks (declared size before extraction; streamed cap during extraction). Confirmed `is_relative_to` runs on the *resolved* target. Confirmed off-host redirects raise. Added the backslash and drive-letter cases after review. |
| R2 | `untrusted.py` | 2026-10-01 | Found and removed a dead `if False` comprehension (AI_LOG #2). Confirmed hidden HTML comments are both *flagged* and *stripped*. Confirmed `wrap_untrusted` is used only in the user message, never in `system`. |
| R3 | API key path: `config.py`, `/api/key`, `ClaudeGenerator.client` | 2026-10-01 | Key held in a locked in-memory store. `/api/status` returns only `"env" | "session" | "none"`. Grepped for `KEYS.get()` call sites: only the client constructor and generator selection, no logging. Basic `sk-ant-` format check to catch paste errors. |
| R4 | Auth middleware in `server.py` | 2026-10-01 | Every `/api/*` route has `dependencies=auth` (grep count matches route count). Query-param token accepted for `<img>`/download GETs only, because they cannot send headers. Host allow-list includes `testserver` for the test client only; harmless on 127.0.0.1. |
| R5 | `engines.install_bridge` (writes into a user project) | 2026-10-01 | Copies only from the bundled bridge tree. The target must look like a UE/Unity project. Never deletes. `dirs_exist_ok` updates an existing bridge in place. |

**Open for the next human pass:** re-verify `data/store_specs.json` against the live Fab and Unity
publisher portals, then set `verified: true` and `last_checked`.
