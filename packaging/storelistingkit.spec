# PyInstaller spec. Two flavours from one spec:
#   SLK_ONEFILE=1 -> dist/StoreListingKit.exe            (portable, single file)
#   default       -> dist/StoreListingKit/StoreListingKit.exe (folder; used by the installer, starts faster)
import os
from pathlib import Path

import storelistingkit
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

onefile = os.environ.get("SLK_ONEFILE") == "1"
datas = collect_data_files("storelistingkit")
# collect_data_files skips *.py, but the Unreal bridge *is* Python (init_unreal.py, slk_bridge.py)
# that must ship as data. Add the bridges tree explicitly (AI_LOG #8).
datas.append((str(Path(storelistingkit.__file__).parent / "bridges"), "storelistingkit/bridges"))
hidden = collect_submodules("uvicorn") + ["storelistingkit.server"]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    datas=datas,
    hiddenimports=hidden,
    excludes=["tkinter", "pytest", "matplotlib", "numpy"],
    noarchive=False,
)
pyz = PYZ(a.pure)
common = dict(name="StoreListingKit", console=True, icon="icon.ico", upx=False)

if onefile:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **common)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **common)
    coll = COLLECT(exe, a.binaries, a.datas, name="StoreListingKit", upx=False)
