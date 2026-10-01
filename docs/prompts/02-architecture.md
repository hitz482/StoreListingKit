# Stage 2 prompt: Architecture

```
You are a senior engineer. Input: docs/PRD.md.
Write docs/ARCHITECTURE.md. Requirements:
- An EngineAdapter contract with Unreal and Unity implementations; both must pass one shared contract test suite.
- Every LLM output is a pydantic model; raw model text never reaches the UI.
- Mark which modules are deterministic. Keep the LLM to a single module behind a protocol so it can be mocked.
- Draw the trust boundaries: what is untrusted, where it is sanitised, what the model can see.
- Local-first: one process that serves a browser UI on 127.0.0.1 and packages with PyInstaller.
List the decisions that deserve ADRs.
```

Human edits: moved "technical details" rendering out of the model and into the profile (fact guard).
