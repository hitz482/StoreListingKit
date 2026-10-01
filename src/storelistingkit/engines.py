"""Connect to locally installed Unreal Engine / Unity: detect installs, install editor bridges.

The bridges (src/storelistingkit/bridges/) add menu items inside the editors that launch this tool
on the current project's plugin and capture screenshots into a folder the tool picks up.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from importlib import resources
from pathlib import Path

from pydantic import BaseModel

APP_DIR_NAME = "StoreListingKit"
UNREAL_BRIDGE = "StoreListingKitBridge"
UNITY_BRIDGE = "com.storelistingkit.bridge"


class EngineInstall(BaseModel):
    engine: str
    version: str
    path: str
    source: str


class BridgeError(ValueError):
    pass


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    return Path(base) / APP_DIR_NAME


def launch_command() -> list[str]:
    """How the editor bridges should start this tool."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "storelistingkit"]


def record_location() -> Path | None:
    """Write where the tool lives so the editor bridges can find it (portable exe or installed)."""
    try:
        d = app_data_dir()
        d.mkdir(parents=True, exist_ok=True)
        cmd = launch_command()
        path = d / "location.json"
        path.write_text(json.dumps({"exe": cmd[0], "args": cmd[1:]}, indent=2), encoding="utf-8")
        return path
    except OSError:
        return None


# --------------------------------------------------------------------------- detection


def _winreg_values(hive_name: str, key_path: str) -> dict[str, dict[str, str]]:
    """Return {subkey: {value_name: value}} for a registry key; empty off Windows."""
    if sys.platform != "win32":
        return {}
    import winreg

    hive = getattr(winreg, hive_name)
    out: dict[str, dict[str, str]] = {}
    try:
        with winreg.OpenKey(hive, key_path) as key:
            # direct values (e.g. Builds: {GUID: path})
            vals: dict[str, str] = {}
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(key, i)
                    vals[name] = str(val)
                    i += 1
                except OSError:
                    break
            if vals:
                out[""] = vals
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(key, i)
                    i += 1
                except OSError:
                    break
                with winreg.OpenKey(key, sub) as sk:
                    svals: dict[str, str] = {}
                    j = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(sk, j)
                            svals[name] = str(val)
                            j += 1
                        except OSError:
                            break
                    out[sub] = svals
    except OSError:
        return {}
    return out


def find_unreal_installs(launcher_dat: Path | None = None) -> list[EngineInstall]:
    found: dict[str, EngineInstall] = {}
    program_data = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    dat = launcher_dat or program_data / "Epic/UnrealEngineLauncher/LauncherInstalled.dat"
    try:
        data = json.loads(dat.read_text(encoding="utf-8"))
        for item in data.get("InstallationList", []):
            app = str(item.get("AppName", ""))
            loc = str(item.get("InstallLocation", ""))
            if app.startswith("UE_") and loc:
                found[loc.lower()] = EngineInstall(engine="unreal", version=app[3:], path=loc, source="Epic Launcher")
    except (OSError, ValueError, AttributeError):
        pass
    for ver, vals in _winreg_values("HKEY_LOCAL_MACHINE", r"SOFTWARE\EpicGames\Unreal Engine").items():
        loc = vals.get("InstalledDirectory")
        if ver and loc and loc.lower() not in found:
            found[loc.lower()] = EngineInstall(engine="unreal", version=ver, path=loc, source="registry")
    builds = _winreg_values("HKEY_CURRENT_USER", r"SOFTWARE\Epic Games\Unreal Engine\Builds").get("", {})
    for guid, loc in builds.items():
        if loc.lower() not in found:
            found[loc.lower()] = EngineInstall(engine="unreal", version=f"source build {guid[:8]}", path=loc,
                                               source="registry (source build)")
    return sorted(found.values(), key=lambda e: e.version)


def _unity_hub_dirs() -> list[Path]:
    dirs: list[Path] = []
    if sys.platform == "win32":
        dirs.append(Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Unity/Hub/Editor")
        secondary = Path(os.environ.get("APPDATA", "")) / "UnityHub/secondaryInstallPath.json"
        try:
            p = json.loads(secondary.read_text(encoding="utf-8"))
            if isinstance(p, str) and p:
                dirs.append(Path(p))
        except (OSError, ValueError):
            pass
    elif sys.platform == "darwin":
        dirs.append(Path("/Applications/Unity/Hub/Editor"))
    else:
        dirs.append(Path.home() / "Unity/Hub/Editor")
    return dirs


def find_unity_installs(hub_dirs: list[Path] | None = None) -> list[EngineInstall]:
    out: list[EngineInstall] = []
    for base in hub_dirs if hub_dirs is not None else _unity_hub_dirs():
        try:
            for child in sorted(base.iterdir()):
                if child.is_dir() and child.name[:1].isdigit():
                    out.append(EngineInstall(engine="unity", version=child.name, path=str(child), source="Unity Hub"))
        except OSError:
            continue
    return out


def find_installs() -> list[EngineInstall]:
    return find_unreal_installs() + find_unity_installs()


# --------------------------------------------------------------------------- bridges


def _bridge_source(name: str) -> Path:
    return Path(str(resources.files("storelistingkit").joinpath(f"bridges/{name}")))


def detect_project(project_dir: Path) -> str:
    if any(project_dir.glob("*.uproject")):
        return "unreal"
    if (project_dir / "Assets").is_dir() and (project_dir / "ProjectSettings").is_dir():
        return "unity"
    raise BridgeError("Not an Unreal project (no .uproject) or Unity project (no Assets/ + ProjectSettings/).")


def install_bridge(project_dir: str | Path) -> dict[str, str]:
    """Copy the matching editor bridge into an Unreal or Unity project and record our location."""
    project = Path(project_dir).expanduser()
    if not project.is_dir():
        raise BridgeError(f"Folder not found: {project}")
    engine = detect_project(project)
    if engine == "unreal":
        src, dest = _bridge_source("unreal/" + UNREAL_BRIDGE), project / "Plugins" / UNREAL_BRIDGE
    else:
        src, dest = _bridge_source("unity/" + UNITY_BRIDGE), project / "Packages" / UNITY_BRIDGE
    if not src.is_dir():
        raise BridgeError("Bridge files are missing from this installation.")
    shutil.copytree(src, dest, dirs_exist_ok=True)
    record_location()
    return {"engine": engine, "installed_to": str(dest)}
