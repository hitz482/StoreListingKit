# Eval rubric

## Extraction (deterministic, runs in CI, no API key)

Each case is a real public, MIT-licensed plugin repo pinned to a commit. Ground truth was labelled by
hand from the descriptor files (`.uplugin`, `package.json`, `.asmdef`), without looking at the extractor's output.

| Field | Points | Scoring |
|-------|--------|---------|
| engine | 1 | exact |
| name | 1 | exact |
| display_name | 1 | exact |
| version | 1 | exact |
| engine_versions | 1 | set equality |
| modules | 2 | F1 of the module-name sets × 2 |
| platforms | 1 | set equality (an empty set means "not restricted / unknown") |
| **invented facts** | −1 each | a module or platform in the output that is in neither the ground truth nor the repo |

Score per case = points / 8. The headline number is the mean over all cases.

## Listing quality (optional, `--generate`, needs `ANTHROPIC_API_KEY`)

For each case: generate per-store copy from the **extracted** profile, then record:
- whether it passed validation on attempt 1, 2 or 3, or failed hard;
- the fact-guard violations caught (these are retries, not output);
- wall-clock seconds per store, which feeds the time-saving estimate in docs/BUSINESS.md.
