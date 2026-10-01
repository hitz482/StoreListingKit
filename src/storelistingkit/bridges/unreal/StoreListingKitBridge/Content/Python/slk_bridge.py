"""Store Listing Kit bridge for Unreal Editor.

Adds Tools > Store Listing Kit:
  - Open Store Listing Kit for a project plugin
  - Capture listing screenshot (viewport, 1920x1080)
  - Open screenshots folder
The tool itself is found via SLK_EXE, %LOCALAPPDATA%/StoreListingKit/location.json (written by the app
on every launch), or the default per-user install folder.
"""

import json
import os
import subprocess
import time

import unreal

BRIDGE_NAME = "StoreListingKitBridge"


def _project_dir():
    return os.path.abspath(unreal.Paths.project_dir())


def screenshots_dir():
    path = os.path.join(_project_dir(), "Saved", "StoreListingKit", "Screenshots")
    os.makedirs(path, exist_ok=True)
    return path


def find_tool():
    env = os.environ.get("SLK_EXE")
    if env and os.path.isfile(env):
        return [env]
    local = os.environ.get("LOCALAPPDATA", "")
    loc = os.path.join(local, "StoreListingKit", "location.json")
    if os.path.isfile(loc):
        try:
            with open(loc, encoding="utf-8") as fh:
                data = json.load(fh)
            if os.path.isfile(data.get("exe", "")):
                return [data["exe"], *data.get("args", [])]
        except (OSError, ValueError):
            pass
    default = os.path.join(local, "Programs", "StoreListingKit", "StoreListingKit.exe")
    if os.path.isfile(default):
        return [default]
    return None


def project_plugins():
    """Plugins inside this project's Plugins/ folder, excluding the bridge itself."""
    root = os.path.join(_project_dir(), "Plugins")
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("Binaries", "Intermediate", "Content", "Source")]
        for name in filenames:
            if name.endswith(".uplugin") and not name.startswith(BRIDGE_NAME):
                found.append(dirpath)
    return sorted(found)


def _choose_plugin():
    plugins = project_plugins()
    if not plugins:
        unreal.EditorDialog.show_message(
            "Store Listing Kit", "No plugins found in this project's Plugins folder.",
            unreal.AppMsgType.OK)
        return None
    if len(plugins) == 1:
        return plugins[0]
    # Ask one plugin at a time; Unreal's Python API has no list picker.
    for path in plugins:
        answer = unreal.EditorDialog.show_message(
            "Store Listing Kit", f"Create a listing for '{os.path.basename(path)}'?",
            unreal.AppMsgType.YES_NO_CANCEL)
        if answer == unreal.AppReturnType.YES:
            return path
        if answer == unreal.AppReturnType.CANCEL:
            return None
    return None


def open_tool():
    tool = find_tool()
    if not tool:
        unreal.EditorDialog.show_message(
            "Store Listing Kit",
            "Store Listing Kit is not installed. Install it, run it once, then try again "
            "(or set the SLK_EXE environment variable).",
            unreal.AppMsgType.OK)
        return
    plugin = _choose_plugin()
    if not plugin:
        return
    args = [*tool, "--source", plugin, "--screenshots", screenshots_dir()]
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(args, creationflags=flags, close_fds=True)
    unreal.log(f"Store Listing Kit launched for {plugin}")


def capture_screenshot():
    name = os.path.join(screenshots_dir(), time.strftime("listing_%Y%m%d_%H%M%S.png"))
    world = None
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    except Exception:
        pass
    unreal.SystemLibrary.execute_console_command(world, f'HighResShot 1920x1080 filename="{name}"')
    unreal.log(f"Store Listing Kit: screenshot requested -> {name}")


def open_screenshots_folder():
    path = screenshots_dir()
    if hasattr(os, "startfile"):
        os.startfile(path)  # noqa: S606 - opens Explorer on our own folder
    else:
        unreal.log(path)


def register_menus():
    menus = unreal.ToolMenus.get()
    tools = menus.find_menu("LevelEditor.MainMenu.Tools")
    if tools is None:
        return
    tools.add_section("StoreListingKit", "Store Listing Kit")
    entries = [
        ("SLK_Open", "Open Store Listing Kit for a project plugin", "slk_bridge.open_tool()"),
        ("SLK_Capture", "Capture listing screenshot (1920x1080)", "slk_bridge.capture_screenshot()"),
        ("SLK_Folder", "Open listing screenshots folder", "slk_bridge.open_screenshots_folder()"),
    ]
    for name, label, command in entries:
        entry = unreal.ToolMenuEntry(name=name, type=unreal.MultiBlockType.MENU_ENTRY)
        entry.set_label(label)
        entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", f"import slk_bridge; {command}")
        tools.add_menu_entry("StoreListingKit", entry)
    menus.refresh_all_widgets()
