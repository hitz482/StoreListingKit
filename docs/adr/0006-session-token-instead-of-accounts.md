# ADR 0006: A per-launch session token instead of user accounts

Status: accepted, 2026-10-01

## Context
The scope cuts say "no user accounts beyond simple auth". Even a server bound to localhost can be
reached by other local processes, and by web pages through DNS rebinding.

## Decision
- Bind to `127.0.0.1` only.
- On each launch, generate a 32-byte random token and open the browser at `/#token=…`. The UI sends
  it as `X-SLK-Token`, and every `/api/*` route checks it in constant time.
- Reject requests whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>`, which blocks
  DNS rebinding.
- Rate-limit generation per token.

## Consequences
+ No passwords to manage. The token dies with the process.
− If the user closes the tab, they reopen it from the URL printed in the console window.
