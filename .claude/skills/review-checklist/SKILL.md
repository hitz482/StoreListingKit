---
name: review-checklist
description: Checklist the reviewer agent applies to every diff in Store Listing Kit.
---
# Review checklist

## Correctness
- [ ] Every new public function has a test, or the hand-off explains why not.
- [ ] Adapter changes come with updated golden files, and the golden diff is intentional.
- [ ] No store limit is hard-coded outside `data/store_specs.json`.

## LLM boundary
- [ ] Every model response is parsed into a pydantic model. No `.text` reaches the UI.
- [ ] Invalid output triggers a retry with feedback, and the final failure raises `GenerationError`.
- [ ] The fact guard runs: generated copy cannot add modules or platforms that are not in the profile.
- [ ] Repo text reaches prompts only through `untrusted.wrap_untrusted()`.

## Security (see SECURITY.md)
- [ ] Zip handling goes through `ingest.safe_extract_zip` (size, count, ratio, traversal and symlink checks).
- [ ] Network fetches go through `ingest.fetch_github_zip` (host allow-list, size cap, timeout).
- [ ] Images are opened only through `images.load_image` (pixel cap, format allow-list).
- [ ] The API key is never logged, written to disk or returned by an endpoint.
- [ ] New `/api/*` routes depend on `require_token`.

## Hygiene
- [ ] `ruff check .` is clean, and `pytest -q` is green.
- [ ] No new dependency without a note.
- [ ] Context changes (CLAUDE.md, skills, agents) use the `context:` prefix and cite an AI_LOG entry.
