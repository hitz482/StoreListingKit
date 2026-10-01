# ADR 0007: Thin editor bridges (UE Python plugin, Unity editor package) that launch the exe

Status: accepted, 2026-10-01 (AI_LOG #4)

## Context
Sellers work inside Unreal Editor and Unity on Windows. Uploading a zip of their own project is
awkward, and screenshots are taken in the editor anyway. A native C++ UE plugin would need compiling
per engine version and platform.

## Decision
- **Unreal:** a content-only plugin (`StoreListingKitBridge`) that depends on the bundled Python Editor
  Script Plugin. `init_unreal.py` registers Tools-menu entries through `unreal.ToolMenus`. No C++, so
  nothing to compile, and one copy works across UE5 versions.
- **Unity:** an embedded UPM package with an editor-only asmdef and `[MenuItem]`s.
- Both bridges only *launch* `StoreListingKit.exe --source <plugin dir> --screenshots <dir>` and capture
  screenshots into a project-local folder. All parsing and generation stay in the app, under one test suite.
- The app installs a bridge into a chosen project (Connect engines → Install bridge). It also writes
  `location.json`, so bridges find a portable or installed exe.

## Consequences
+ No per-engine-version builds. Editor code is about 150 lines per engine.
− Unreal needs the Python Editor Script Plugin (bundled with UE5 and enabled by the bridge's dependency).
− The bridges are not exercised in CI (no engine on the runners). Their JSON descriptors and the
  install path are tested, and the editor behaviour is on the manual QA checklist (docs/WINDOWS.md).
