"""Engine connection: install detection and editor-bridge installation."""

import json

import pytest

from storelistingkit import engines
from storelistingkit.adapters import extract_profile


def test_unreal_launcher_dat_parsed(tmp_path):
    dat = tmp_path / "LauncherInstalled.dat"
    dat.write_text(json.dumps({"InstallationList": [
        {"InstallLocation": "C:/Epic/UE_5.4", "AppName": "UE_5.4"},
        {"InstallLocation": "C:/Epic/Fortnite", "AppName": "Fortnite"},
    ]}))
    found = engines.find_unreal_installs(dat)
    assert [(e.version, e.path) for e in found] == [("5.4", "C:/Epic/UE_5.4")]


def test_unity_hub_dirs_listed(tmp_path):
    (tmp_path / "2022.3.20f1").mkdir()
    (tmp_path / "6000.0.23f1").mkdir()
    (tmp_path / "modules.json").write_text("{}")
    found = engines.find_unity_installs([tmp_path, tmp_path / "missing"])
    assert [e.version for e in found] == ["2022.3.20f1", "6000.0.23f1"]


def test_install_bridge_into_unreal_project(tmp_path):
    proj = tmp_path / "MyGame"
    proj.mkdir()
    (proj / "MyGame.uproject").write_text("{}")
    r = engines.install_bridge(proj)
    assert r["engine"] == "unreal"
    assert (proj / "Plugins/StoreListingKitBridge/StoreListingKitBridge.uplugin").is_file()
    assert (proj / "Plugins/StoreListingKitBridge/Content/Python/init_unreal.py").is_file()
    assert (engines.app_data_dir() / "location.json").is_file()


def test_install_bridge_into_unity_project(tmp_path):
    proj = tmp_path / "UnityGame"
    (proj / "Assets").mkdir(parents=True)
    (proj / "ProjectSettings").mkdir()
    r = engines.install_bridge(proj)
    assert r["engine"] == "unity"
    assert (proj / "Packages/com.storelistingkit.bridge/Editor/StoreListingKitBridge.cs").is_file()


def test_install_bridge_rejects_non_project(tmp_path):
    with pytest.raises(engines.BridgeError):
        engines.install_bridge(tmp_path)


def test_bridge_is_not_mistaken_for_the_users_plugin(tmp_path, fixtures):
    """A project with the bridge installed must still describe the user's plugin, not the bridge."""
    import shutil

    proj = tmp_path / "UnityGame"
    shutil.copytree(fixtures / "unity_basic", proj)
    (proj / "Assets").mkdir(exist_ok=True)
    engines.install_bridge(proj)
    p = extract_profile(proj)
    assert p.name == "com.example.tweenkit"
    assert "StoreListingKit.Bridge.Editor" not in p.module_names()


def test_bridge_descriptors_are_valid_json():
    root = engines._bridge_source("unreal/StoreListingKitBridge")
    data = json.loads((root / "StoreListingKitBridge.uplugin").read_text())
    assert any(p["Name"] == "PythonScriptPlugin" for p in data["Plugins"])
    pkg = json.loads((engines._bridge_source("unity/com.storelistingkit.bridge") / "package.json").read_text())
    assert pkg["name"] == "com.storelistingkit.bridge"


def test_location_records_launch_command():
    path = engines.record_location()
    data = json.loads(path.read_text())
    assert data["exe"] and isinstance(data["args"], list)
