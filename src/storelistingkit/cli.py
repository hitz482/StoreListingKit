"""Command line entry point. `storelistingkit` with no arguments starts the local app."""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

from . import __version__


def _free_port(preferred: int) -> int:
    for port in ([preferred] if preferred else []) + [0]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("No free port")


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from . import engines
    from .server import AppState, create_app, new_token, preload

    port = _free_port(args.port)
    state = AppState(token=new_token(), port=port)
    try:
        preload(state, args.source, args.screenshots)
    except Exception as exc:  # noqa: BLE001 - show and continue without the preload
        print(f"Could not load {args.source}: {exc}", file=sys.stderr)
    engines.record_location()
    app = create_app(state)
    url = f"http://127.0.0.1:{port}/#token={state.token}"
    print(f"Store Listing Kit {__version__}")
    print(f"Open: {url}")
    print("Keep this window open while you use the app. Press Ctrl+C to quit.", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    finally:
        state.cleanup()
    return 0


def _materialize(source: str, work: Path) -> Path:
    from .ingest import copy_local_folder, fetch_github_zip, safe_extract_zip

    if source.startswith("https://"):
        return safe_extract_zip(fetch_github_zip(source), work)
    p = Path(source)
    if p.is_file() and p.suffix.lower() == ".zip":
        return safe_extract_zip(p, work)
    return copy_local_folder(p, work)


def cmd_extract(args: argparse.Namespace) -> int:
    from .adapters import extract_profile

    with tempfile.TemporaryDirectory(prefix="slk-") as tmp:
        profile = extract_profile(_materialize(args.source, Path(tmp)))
    print(profile.model_dump_json(indent=2))
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    """End-to-end offline check of the packaged app: extract → images → template copy → export zip."""
    import io
    import zipfile
    from importlib import resources

    from PIL import Image

    from .adapters import extract_profile
    from .exporter import build_zip
    from .generator import TemplateGenerator
    from .images import build_store_images
    from .models import ENGINE_STORES, ListingKit
    from .stores import validate_copy, validate_images

    sample = Path(str(resources.files("storelistingkit").joinpath("data/sample_plugin")))
    with tempfile.TemporaryDirectory(prefix="slk-selftest-") as tmp:
        tmpd = Path(tmp)
        shot = tmpd / "shot.png"
        Image.new("RGB", (1280, 720), (40, 90, 160)).save(shot)
        profile = extract_profile(sample)
        assert profile.name, "extraction failed"
        kit = ListingKit(profile=profile)
        for store in ENGINE_STORES[profile.engine]:
            imgs = build_store_images(store, [shot], profile.title, tmpd / "images" / store.value)
            kit.images += imgs
            copy = TemplateGenerator().generate(profile, store)
            kit.copies[store] = copy
            kit.issues += validate_copy(copy) + validate_images(store, imgs, 1)
        data = build_zip(kit, tmpd / "images")
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    bridges = Path(str(resources.files("storelistingkit").joinpath("bridges")))
    required = ["unreal/StoreListingKitBridge/StoreListingKitBridge.uplugin",
                "unreal/StoreListingKitBridge/Content/Python/init_unreal.py",
                "unreal/StoreListingKitBridge/Content/Python/slk_bridge.py",
                "unity/com.storelistingkit.bridge/package.json",
                "unity/com.storelistingkit.bridge/Editor/StoreListingKitBridge.cs"]
    missing = [r for r in required if not (bridges / r).is_file()]
    result = {"ok": not missing, "missing_bridge_files": missing, "engine": profile.engine.value,
              "name": profile.name, "files": len(names),
              "errors": [i.message for i in kit.issues if i.severity.value == "error"]}
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="storelistingkit", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd")

    def add_serve_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--port", type=int, default=8765)
        p.add_argument("--no-browser", action="store_true")
        p.add_argument("--source", help="Local plugin folder to open (used by the editor bridges).")
        p.add_argument("--screenshots", help="Folder of screenshots to preload.")

    add_serve_args(parser)
    add_serve_args(sub.add_parser("serve", help="Start the local app (default)."))
    p_extract = sub.add_parser("extract", help="Print the extracted profile as JSON.")
    p_extract.add_argument("source", help="Folder, .zip file, or https://github.com/owner/repo URL")
    sub.add_parser("selftest", help="Run an offline end-to-end check and exit.")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.cmd == "extract":
        return cmd_extract(args)
    if args.cmd == "selftest":
        return cmd_selftest(args)
    return cmd_serve(args)
