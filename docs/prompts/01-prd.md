# Stage 1 prompt: PRD

Used with Claude (Claude Code session) to turn the hackathon plan into a PRD.

```
You are a product manager. Input: the attached hackathon plan ("Store Listing Kit: Plan to Score 90+").
Write docs/PRD.md for a tool that turns a game-engine plugin repo plus real screenshots into
ship-ready store listings for Fab (Unreal) and the Unity Asset Store.

Constraints:
- One journey only: connect repo -> editable extracted profile -> screenshots -> generate -> review/edit -> export zip.
- Number the functional requirements (F1..Fn) so tasks and tests can cite them.
- State the non-functional requirements that protect factual accuracy and security.
- Copy the plan's scope cuts verbatim into "Out of scope".
- Success metrics must be measurable by the eval harness or a stopwatch, nothing else.
- The deliverable must also run as a Windows .exe with no Python install.
Do not invent store limits; reference a data file the engineers will verify.
```

Human edits after generation: added F9 (Windows exe), tightened the "facts are never invented" NFR.
