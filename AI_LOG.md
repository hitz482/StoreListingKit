# AI_LOG

A running log of where AI-assisted development went wrong, why, and what changed as a result.
Started on day one (2026-10-01), before the first line of code.
Rule: an entry records only something that actually happened, with evidence a reviewer can check
(a test, a diff, a command output). Context files (CLAUDE.md, skills, agents) may cite only entries
that exist.

**Template**
```
## #N: title (date)
- What failed:
- Root cause: missing context | wrong instruction | model limit | environment
- Fix:
- Evidence (before → after):
- Context change: (CLAUDE.md / skill / agent edit, if any)
```

---

## #1: Context files cited AI_LOG entries that did not exist yet (2026-10-01)
- **What failed:** the first drafts of `.claude/skills/extraction-guardrails/SKILL.md` and
  `.claude/agents/test-writer.md` justified their rules with "(AI_LOG #1, #2)" and "(see AI_LOG #3)".
  Those entries did not exist. The model invented plausible provenance.
- **Root cause:** model limit. It pattern-matched the plan's example ("cite the AI_LOG entry")
  without checking that the target existed.
- **Fix:** removed the citations before the first commit. Added the rule at the top of this file:
  context may cite only entries that exist.
- **Evidence:** no commit ever contained the fabricated references (`git log -p -S "AI_LOG #"` shows only
  real citations: #8 and #10).
- **Context change:** the rule above, plus the review-checklist item "Context changes … cite an AI_LOG entry".

## #2: Dead code in the prompt-injection module (2026-10-01)
- **What failed:** the first draft of `untrusted.readme_excerpt()` contained
  `detect_injection(text) + [f for f in detect_injection(...) if False]`, a comprehension that can
  never add anything, in a security-relevant function.
- **Root cause:** model limit. A half-finished idea (scan text with HTML comments stripped) was left in.
- **Fix:** rewritten to scan the full text, then scan hidden HTML comments separately.
  `test_hidden_comment_injection_still_flagged` pins the intended behaviour.
- **Evidence:** `tests/test_untrusted.py`.
- **Context change:** `untrusted.py` is listed as a HUMAN GATE in CLAUDE.md rule 7. Review note R2 in
  docs/REVIEW_NOTES.md.

## #3: Fact guard would have rejected the ordinary word "switch" (2026-10-01)
- **What failed:** the platform scan in `generator.fact_guard()` matched bare `switch`, so copy like
  "Switch outline styles at runtime" would count as claiming Nintendo Switch support. That causes
  needless retries and, after three attempts, a hard failure on valid copy.
- **Root cause:** wrong instruction. The platform word list doubled as both normaliser and scanner.
- **Fix:** split it into `KNOWN_PLATFORMS` (normalisation) and `SCAN_WORDS` (prose scan, with only
  "nintendo switch").
- **Evidence:** `test_fact_guard_ignores_plain_word_switch`.

## #4: The plan assumed a hosted web app; users need it on Windows, next to their engines (2026-10-01)
- **What failed:** the PRD and ADR 0001 as first drafted described a browser app with zip/URL input
  only. Mid-build the user clarified that sellers must *install it on Windows* and *connect it to
  Unreal and Unity*.
- **Root cause:** missing context. The plan never said where the users work: inside the editors,
  on Windows.
- **Fix:** added a per-user Inno Setup installer, editor bridges (UE plugin with a Python menu, Unity
  editor package), engine-install detection, a local-folder source and CLI flags `--source/--screenshots`.
  ADR 0007 records the decision.
- **Evidence:** `tests/test_engines.py`, `packaging/installer.iss`, and the CI job "Windows exe + installer",
  which silently installs and runs the installed exe.
- **Context change:** PRD F10–F12, an ARCHITECTURE section on engines, and a CLAUDE.md overview line.

## #5: Wrong provenance for merged dependencies (2026-10-01)
- **What failed:** the golden file showed `sources.dependencies = "QuickOutline.uplugin"`, but the list
  also held modules parsed from `*.Build.cs`. The provenance UI would have told users the wrong file.
- **Root cause:** model limit. `setdefault` kept the first source and silently dropped the second.
- **Fix:** sources now record both, e.g. `"QuickOutline/QuickOutline.uplugin, Source/*/*.Build.cs"`.
- **Evidence:** `tests/fixtures/golden/unreal_basic.json`. Caught by reading the golden file before
  committing it, which is why the golden test fails, not passes, when a golden file is missing.

## #6: The installed bridge could be mistaken for the user's own plugin (2026-10-01)
- **What failed (caught by design review, before it shipped):** the Unity bridge opens the tool on the
  project root. The bridge's own `Packages/com.storelistingkit.bridge/package.json` then sits at the
  same depth as the user's package, so the "shallowest package" rule could describe *our* bridge.
- **Root cause:** missing context. The adapters did not know the bridges exist.
- **Fix:** both adapters skip the bridge descriptors.
- **Evidence:** `test_bridge_is_not_mistaken_for_the_users_plugin`.

## #7: Session URL never printed when stdout was not a console (2026-10-01)
- **What failed:** smoke-testing the frozen binary with output redirected to a log showed an empty log.
  The token URL was stuck in the stdout buffer while uvicorn blocked, so the API answered 401 because
  the test could not read the token.
- **Root cause:** model limit. `print()` was written assuming an interactive console.
- **Fix:** `print(..., flush=True)` before starting the server.
- **Evidence:** before, `frozen.log` was empty and the call returned `{"detail":"Missing or invalid session token."}`.
  After, the log shows the URL and the bridge install returns 200.

## #8: The exe silently shipped without the Unreal bridge's Python files (2026-10-01)
- **What failed:** after #7, "Install bridge" from the frozen binary created only
  `Plugins/StoreListingKitBridge/StoreListingKitBridge.uplugin`. `Content/Python/init_unreal.py` and
  `slk_bridge.py` were missing, so the plugin would load in UE with no menus. The tests were green,
  because they run from source.
- **Root cause:** model limit. The spec assumed `collect_data_files()` bundles everything, but by
  default it skips `*.py`, and the UE bridge *is* Python shipped as data.
- **Fix:** the spec adds the bridges tree explicitly. `selftest` now fails when any bridge file is
  missing, and CI runs `selftest` against both built exes and the *installed* exe.
- **Evidence:** before, `find UEProj -type f` listed 1 bridge file. After, the selftest prints
  `"missing_bridge_files": []`.
- **Lesson:** test the artifact you ship, not only the source tree.

## #9: GitHub archive downloads blocked in the dev sandbox (2026-10-01)
- **What failed:** `codeload.github.com` returned 403 inside the cloud dev container, so the eval
  harness could not fetch repos the way the app does.
- **Root cause:** environment (network policy). `git` over the proxy worked.
- **Fix:** evals fetch each case with `git fetch --depth 1 <pinned commit>`. This is also more
  reproducible than "HEAD of a branch".
- **Evidence:** `evals/run_evals.py::checkout`, `evals/cases.json` (commit SHAs).

## #10: The eval harness found three extraction errors the unit tests missed (2026-10-01)
- **What failed:** baseline 97.9% (8/10 perfect, see `evals/results_baseline.md`):
  - KawaiiPhysics: `platforms` reported Win64/Mac/Linux, which was the union of the *editor and test*
    modules' allow-lists, while the runtime modules are unrestricted. That understates support in a
    store listing.
  - KawaiiPhysics: the `KawaiiPhysicsTests` module was listed as a buyer-facing module.
  - UI Particle: the `Coffee.UIParticle.Demo` assembly under `Samples~/` was listed. Unity ignores
    `~` folders.
- **Root cause:** missing context. The extraction-guardrails skill did not define what "platforms"
  means for a plugin, or which modules count.
- **Fix:** platforms are reported only when *every* runtime module is restricted. Test modules are
  skipped. `~` folders are skipped. Regression tests use minimal fixtures.
- **Evidence:** before 97.9% → after **100% (10/10)**, see `evals/results.md`. CI gates on ≥95%.
- **Context change:** extraction-guardrails rules 9–11.

---

## Lessons so far
1. **Test the shipped artifact.** Two of the ten issues (#7, #8) were invisible to a green test suite
   and only showed up when the frozen binary was run. CI now smoke-tests the exe and the installed exe.
2. **Real repos beat fixtures.** Hand-written fixtures encode what we already believe. The eval
   harness on 10 public repos found the platform and test-module errors (#10).
3. **Deterministic guards make AI output safe to retry.** The fact guard and the schema turn
   hallucinations into retries with feedback, not into wrong listings. Guards need their own false-positive
   tests (#3).
4. **Context drifts when requirements change.** The Windows and engine requirement (#4) touched the
   PRD, the ADRs, the architecture and the code. Updating the context first kept the agents aligned.
5. **AI invents provenance** (#1) as readily as it invents facts. Citations need checking too.
