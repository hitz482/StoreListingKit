# Windows: install, connect Unreal and Unity, and build

## Install (sellers)

1. Download **`StoreListingKit-Setup-x.y.z.exe`** from the latest
   [GitHub Release](../../releases) (or from the `StoreListingKit-windows` artifact of a CI run).
2. Run it. It installs for your user only (no admin rights) into
   `%LOCALAPPDATA%\Programs\StoreListingKit` and adds Start-menu entries.
   - The exe is not code-signed yet. If SmartScreen appears, choose **More info → Run anyway**.
3. Start **Store Listing Kit** from the Start menu. A console window opens (keep it open) and your
   browser opens the app. Close the console window to quit.

Prefer no installer? Download the portable **`StoreListingKit.exe`** and double-click it.

### Optional: Claude-written copy
Without a key the app makes an offline draft from your repo's own text. For Claude-written copy, either:
- click **API key** in the app (kept in memory for the session only), or
- set it for your user: `setx ANTHROPIC_API_KEY "sk-ant-..."`, then restart the app.

## Connect Unreal Engine and Unity

In the app, click **Connect engines**:
- It lists the Unreal Engine versions (Epic Launcher and source builds) and Unity Hub editors found on this PC.
- Paste a **project folder** and click **Install bridge**:
  - Unreal project (has a `.uproject`): installs `Plugins/StoreListingKitBridge`.
  - Unity project (has `Assets/` and `ProjectSettings/`): installs `Packages/com.storelistingkit.bridge`.
- Restart the editor.

You can also copy the bridges by hand from `%LOCALAPPDATA%\Programs\StoreListingKit\EditorBridges`
(Start menu → *Editor bridges folder*).

### In Unreal Editor (UE 5.x)
**Tools → Store Listing Kit**:
- *Open Store Listing Kit for a project plugin*: picks a plugin under your project's `Plugins/`, then
  launches the app with that plugin already loaded, along with any screenshots you captured.
- *Capture listing screenshot (1920x1080)*: runs `HighResShot` into
  `Saved/StoreListingKit/Screenshots`.
- *Open listing screenshots folder*.

The bridge needs the **Python Editor Script Plugin**, which ships with UE5. The bridge enables it as
a dependency, and UE may ask to restart once.

### In Unity (2021.3+)
**Tools → Store Listing Kit**:
- *Open for Selected Package or Project*: select your package folder in the Project window first (or
  nothing, to scan the project). The app opens with it loaded.
- *Capture Game View Screenshot*: saves into `<Project>/StoreListingKit/Screenshots`. The Game view
  must be visible.
- *Open Screenshots Folder*, and *Forget Tool Location*.

The bridges find the app through `SLK_EXE`, then `%LOCALAPPDATA%\StoreListingKit\location.json`
(written each time the app starts), then the default install folder. In Unity, as a last resort,
a file picker asks for it.

### Manual QA checklist for the bridges (not covered by CI: no engines on CI runners)
- [ ] UE 5.x: the menu appears after a restart; *Open* launches the app with the plugin loaded; *Capture* writes a PNG.
- [ ] Unity 2021.3 / 2022.3 / 6000: the menu appears; *Open* with a package selected loads that package; *Capture* writes a PNG.

## Build it yourself

```powershell
git clone https://github.com/hitz482/StoreListingKit
cd StoreListingKit
.\scripts\setup.ps1        # venv + deps + tests
.\scripts\build_exe.ps1    # dist\StoreListingKit.exe, dist\StoreListingKit\..., and the installer if Inno Setup 6 is installed
```
CI does the same on every push (`.github/workflows/ci.yml`, job *Windows exe + installer*). It
smoke-tests both exes and a silent install, and attaches them to a GitHub Release when you push a
`v*` tag.
