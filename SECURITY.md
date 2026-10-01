# Security checklist (executed)

Each item lists where it is enforced and how it is tested. "Manual" means a human checked it; see
[docs/REVIEW_NOTES.md](docs/REVIEW_NOTES.md).

| # | Item | Enforcement | Test / evidence |
|---|------|-------------|-----------------|
| 1 | **Auth**: per-launch random token on every `/api/*` route, compared in constant time | `server.require_token`, `secrets.token_urlsafe(32)`, `hmac.compare_digest` | `test_requires_token` |
| 2 | **Localhost only**, plus a Host-header allow-list (DNS-rebinding defence) | `cli._free_port` binds 127.0.0.1; `server.host_guard` | `test_rejects_foreign_host` |
| 3 | **Zip bomb**: declared-size cap, streamed-bytes cap, per-entry ratio cap, entry-count cap | `ingest.safe_extract_zip` | `test_rejects_zip_bomb_by_ratio`, `…oversized_unpacked_total`, `…too_many_files` |
| 4 | **Path traversal**: `..`, absolute paths, drive letters, backslashes; resolved-path containment | `ingest._safe_member_path` + `is_relative_to` | `test_rejects_path_traversal` (5 variants), `test_upload_rejects_traversal_zip` |
| 5 | **Symlinks and encrypted entries** rejected; symlinks never followed when walking | `ingest`, `adapters.base.walk` | `test_rejects_symlinks` |
| 6 | **Size limits**: upload 100 MB, unpacked 500 MB, 20k files, images 20 MB / 40 MP / 20 files | `config.Limits` (env-overridable) | `test_rejects_oversized_upload`, server screenshot test |
| 7 | **Image decoding**: format allow-list (PNG/JPEG/WebP), `MAX_IMAGE_PIXELS` decompression-bomb guard, full decode before use | `images.load_image` | server test: a non-image named `.png` is rejected |
| 8 | **SSRF**: only `https://github.com/<owner>/<repo>`; downloads only from `codeload.github.com`; redirects off-host refused; streamed size cap; timeout | `ingest.parse_github_url`, `_NoRedirect`, `fetch_github_zip` | `test_github_url_rejected` (8 variants) |
| 9 | **Rate limiting**: generations per minute (default 6) | `server.check_rate` | `test_rate_limit` |
| 10 | **Secrets**: API key from env or in memory only; never logged, persisted or returned | `config._KeyStore`; `/api/status` reports only the source | `test_key_is_never_returned`; manual review R3 |
| 11 | **Prompt injection**: README treated as untrusted; bounded excerpt; hidden carriers stripped (HTML comments, bidi/zero-width chars); delimiter neutralised; system prompt says tag content is data; user warned in the UI | `untrusted.py`, `generator.SYSTEM_PROMPT` | `test_untrusted.py`, `test_request_shape`, `test_readme_injection_is_flagged` |
| 12 | **Output-side containment**: schema validation, store limits and the fact guard. Raw model text never reaches the UI | `generator.ClaudeGenerator.generate` | `test_hard_failure_after_max_attempts`, `test_fact_guard_*` |
| 13 | **No code execution** from uploaded repos (parse only) | adapters use `json` and regexes only | code review; grep shows no `exec`/`eval`/`subprocess` in `adapters/` or `ingest.py` |
| 14 | **XSS**: the UI renders server data with `textContent` only; strict CSP (`script-src 'self'`, no inline) | `static/app.js` `el()` helper; `server.host_guard` headers | `test_index_served_with_csp` |
| 15 | **Dependency audit** | `pip-audit` in CI (`audit` job) | CI |
| 16 | **Errors don't leak internals**: unexpected exceptions are logged to the console; the UI gets a generic message | `server.run_job` | `test_generation_error_surfaces_cleanly` |

Known limitations:
- The exe is unsigned, so Windows SmartScreen shows "Unknown publisher". Code signing needs a certificate (post-hackathon).
- The token sits in the URL fragment (never sent to the server or logs) and then in `sessionStorage`
  for the tab's lifetime.

Report a vulnerability by opening a private security advisory on the GitHub repository.
