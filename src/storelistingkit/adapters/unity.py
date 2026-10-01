"""Unity adapter: UPM package.json, *.asmdef, ProjectSettings/ProjectVersion.txt."""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Engine, Module, PluginProfile
from .base import EngineAdapter, apply_readme, loads_lenient, read_text, rel, walk

_UNITY_VERSION = re.compile(r"^m_EditorVersion:\s*(\d+)\.(\d+)", re.MULTILINE)


def _short_unity(v: str) -> str:
    m = re.match(r"^\s*(\d+)\.(\d+)", v or "")
    return f"{m.group(1)}.{m.group(2)}" if m else ""


class UnityAdapter(EngineAdapter):
    engine = Engine.UNITY

    def _find_package_json(self, root: Path) -> tuple[Path, dict] | None:
        best: tuple[int, str, Path, dict] | None = None
        for p in walk(root):
            if p.name != "package.json" or p.parent.name == "com.storelistingkit.bridge":
                continue
            text = read_text(p)
            if not text:
                continue
            try:
                data = loads_lenient(text)
            except ValueError:
                continue
            # A UPM package has a reverse-DNS name and/or a "unity" field. npm packages have neither.
            is_upm = "unity" in data or re.match(r"^[a-z0-9-]+(\.[a-z0-9_-]+){2,}$", str(data.get("name", "")))
            if not is_upm:
                continue
            key = (len(p.relative_to(root).parts), str(p))
            if best is None or key < best[:2]:
                best = (*key, p, data)
        return (best[2], best[3]) if best else None

    def _asmdefs(self, root: Path) -> list[Path]:
        # Unity ignores folders ending in "~" (e.g. Samples~), so their assemblies never ship as-is.
        return [p for p in walk(root)
                if p.suffix.lower() == ".asmdef" and "com.storelistingkit.bridge" not in p.parts
                and not any(part.endswith("~") for part in p.relative_to(root).parts)]

    def detect(self, root: Path) -> float:
        try:
            if self._find_package_json(root):
                return 0.95
            if self._asmdefs(root):
                return 0.8
            if (root / "ProjectSettings" / "ProjectVersion.txt").is_file() or (root / "Assets").is_dir():
                return 0.5
        except Exception:  # noqa: BLE001 - contract: detect never raises
            return 0.0
        return 0.0

    def extract(self, root: Path) -> PluginProfile:
        profile = PluginProfile(engine=Engine.UNITY)
        pkg = self._find_package_json(root)
        pkg_dir = pkg[0].parent if pkg else None
        if pkg:
            self._apply_package(profile, pkg[1], rel(root, pkg[0]))
        else:
            profile.warnings.append("No UPM package.json found; name and version need manual entry.")

        pv = root / "ProjectSettings" / "ProjectVersion.txt"
        if not profile.engine_versions and pv.is_file():
            m = _UNITY_VERSION.search(read_text(pv) or "")
            if m:
                profile.engine_versions = [f"{m.group(1)}.{m.group(2)}"]
                profile.sources["engine_versions"] = rel(root, pv)

        self._apply_asmdefs(root, pkg_dir, profile)
        apply_readme(root, profile, near=pkg_dir)
        return profile

    def _apply_package(self, profile: PluginProfile, data: dict, src: str) -> None:
        def put(field: str, value) -> None:
            if value:
                setattr(profile, field, value)
                profile.sources[field] = src

        put("name", str(data.get("name") or "").strip())
        put("display_name", str(data.get("displayName") or "").strip())
        put("version", str(data.get("version") or "").strip())
        put("description", str(data.get("description") or "").strip())
        author = data.get("author")
        put("author", str(author.get("name", "") if isinstance(author, dict) else author or "").strip())
        uv = _short_unity(str(data.get("unity") or ""))
        put("engine_versions", [uv] if uv else [])
        kws = data.get("keywords")
        put("keywords", [str(k) for k in kws] if isinstance(kws, list) else [])
        put("license", str(data.get("license") or "").strip())
        put("docs_url", str(data.get("documentationUrl") or "").strip())
        deps = data.get("dependencies")
        put("dependencies", sorted(str(k) for k in deps) if isinstance(deps, dict) else [])

    def _apply_asmdefs(self, root: Path, pkg_dir: Path | None, profile: PluginProfile) -> None:
        files = self._asmdefs(pkg_dir or root)
        modules: list[Module] = []
        platforms: list[str] = []
        for f in sorted(files):
            text = read_text(f)
            if not text:
                continue
            try:
                data = loads_lenient(text)
            except ValueError:
                profile.warnings.append(f"{rel(root, f)}: could not parse")
                continue
            name = str(data.get("name") or "").strip()
            if not name:
                continue
            # Skip test assemblies; buyers don't care and they inflate the module list.
            refs = [str(r) for r in data.get("optionalUnityReferences") or []]
            if "TestAssemblies" in refs or name.lower().endswith((".tests", ".test")):
                continue
            include = [str(p) for p in data.get("includePlatforms") or []]
            kind = "editor" if include == ["Editor"] else "runtime"
            plats = [p for p in include if p != "Editor"]
            modules.append(Module(name=name, kind=kind, platforms=plats))
            for p in plats:
                if p not in platforms:
                    platforms.append(p)
        if modules:
            modules.sort(key=lambda m: m.kind == "editor")  # runtime assemblies first, stable otherwise
            profile.modules = modules
            profile.sources["modules"] = "*.asmdef"
        if platforms:
            profile.platforms = platforms
            profile.sources["platforms"] = "*.asmdef"
