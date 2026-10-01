# ADR 0001: Local web UI packaged as a Windows exe (not a CLI, not a hosted site)

Status: accepted, 2026-10-01

## Context
The plan asks for a deployed web product, and the team asked for a Windows tool or `.exe`. The
journey has six steps, including editing a structured profile and reviewing copy with live
character counters. A CLI is a poor fit for both. A hosted site would need accounts, upload
storage and a shared API key.

## Decision
One Python process (FastAPI + Uvicorn) serves a static single-page UI on `127.0.0.1` and opens the
browser. PyInstaller packages it as `StoreListingKit.exe`. The same code runs as
`python -m storelistingkit` on any OS and can be deployed behind a reverse proxy later.

## Consequences
+ Web UX (forms, previews, progress) without a hosting bill or user accounts.
+ Each user's API key and files stay on their own machine.
− The exe is about 40–60 MB. Windows SmartScreen warns on an unsigned binary (we document this).
− A localhost server still needs auth against other local processes and DNS rebinding (ADR 0006).
