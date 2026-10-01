# ADR 0002: One provider (Claude Opus 5.5) with structured output, retry and a hard failure

Status: accepted, 2026-10-01

## Context
Listing copy needs strong writing *and* strict adherence to limits and facts. The scope cuts rule
out multiple providers.

## Decision
- Model: `claude-opus-5-5` by default, overridable with `SLK_MODEL`.
- `client.beta.messages.parse(output_format=StoreCopyDraft)` returns a pydantic-validated object.
- Server-side refusal fallback is on (`fallbacks="default"`, beta `server-side-fallback-2026-07-01`).
- After parsing we run our own checks: store character limits and the fact guard. On failure we retry
  with the list of problems, up to `SLK_MAX_ATTEMPTS` (3) times in total, then raise `GenerationError`.
- With no key configured, a deterministic `TemplateGenerator` produces an offline draft that is
  clearly labelled as such.

## Consequences
+ Raw model text never reaches the UI: it is either a validated `StoreCopy` or a clean error.
+ The generator sits behind a protocol, so integration tests mock it in CI at no cost.
− Each attempt costs a full call, so at most `max_attempts` calls per store.
