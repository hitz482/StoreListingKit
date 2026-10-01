"""Unreal Engine plugin adapter: .uplugin + Source/<Module>/<Module>.Build.cs."""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Engine, Module, PluginProfile
from .base import EngineAdapter, apply_readme, loads_lenient, read_text, rel, walk

_DEP_RE = re.compile(
    r"(Public|Private)DependencyModuleNames\s*\.\s*AddRange\s*\(\s*new\s+string\s*\[\s*\]\s*\{(?P<body>[^}]*)\}",
    re.DOTALL,
)
_STR_RE = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"')
# Engine modules everybody depends on; they are noise in a listing.
_TRIVIAL_DEPS = {"Core", "CoreUObject", "Engine", "Slate", "SlateCore", "InputCore"}


_EDITOR_TYPES = ("Editor", "UncookedOnly", "Developer", "Program")


def _is_test_module(name: str) -> bool:
    return name.endswith(("Test", "Tests"))


def _engine_version(raw: str) -> str:
    m = re.match(r"^\s*(\d+)\.(\d+)", raw or "")
    return f"{m.group(1)}.{m.group(2)}" if m else ""


class UnrealAdapter(EngineAdapter):
    engine = Engine.UNREAL

    def _find_uplugin(self, root: Path) -> Path | None:
        found = [p for p in walk(root) if p.suffix.lower() == ".uplugin" and p.stem != "StoreListingKitBridge"]
        if not found:
            return None
        return min(found, key=lambda p: (len(p.relative_to(root).parts), str(p)))

    def detect(self, root: Path) -> float:
        try:
            if self._find_uplugin(root):
                return 1.0
            if any(p.name.endswith(".Build.cs") for p in walk(root, max_depth=5)):
                return 0.6
        except Exception:  # noqa: BLE001 - contract: detect never raises
            return 0.0
        return 0.0

    def extract(self, root: Path) -> PluginProfile:
        profile = PluginProfile(engine=Engine.UNREAL)
        uplugin = self._find_uplugin(root)
        plugin_dir = uplugin.parent if uplugin else root

        if uplugin is not None:
            src = rel(root, uplugin)
            data: dict = {}
            text = read_text(uplugin)
            if text is None:
                profile.warnings.append(f"{src}: unreadable or too large")
            else:
                try:
                    data = loads_lenient(text)
                except ValueError as exc:
                    profile.warnings.append(f"{src}: could not parse ({exc.__class__.__name__})")
            self._apply_descriptor(profile, data, src, uplugin.stem)
        else:
            profile.warnings.append("No .uplugin file found; profile built from Build.cs files only.")

        self._apply_build_files(root, plugin_dir, profile)
        apply_readme(root, profile, near=plugin_dir)
        return profile

    def _apply_descriptor(self, profile: PluginProfile, data: dict, src: str, stem: str) -> None:
        def put(field: str, value) -> None:
            if value:
                setattr(profile, field, value)
                profile.sources[field] = src

        put("name", stem)
        put("display_name", str(data.get("FriendlyName") or "").strip())
        put("version", str(data.get("VersionName") or data.get("Version") or "").strip())
        put("description", str(data.get("Description") or "").strip())
        put("author", str(data.get("CreatedBy") or "").strip())
        put("category", str(data.get("Category") or "").strip())
        put("docs_url", str(data.get("DocsURL") or "").strip())
        put("support_url", str(data.get("SupportURL") or "").strip())
        ev = _engine_version(str(data.get("EngineVersion") or ""))
        put("engine_versions", [ev] if ev else [])

        modules: list[Module] = []
        for m in data.get("Modules") or []:
            if not isinstance(m, dict) or not m.get("Name") or _is_test_module(str(m["Name"])):
                continue
            plats = [str(p) for p in (m.get("PlatformAllowList") or m.get("WhitelistPlatforms") or [])]
            modules.append(Module(name=str(m["Name"]), kind=str(m.get("Type") or ""), platforms=plats))
        put("modules", modules)
        # A platform list is only a fact when *every* runtime module is restricted. If any runtime
        # module has no allow-list it runs everywhere the engine does, and the union of editor-module
        # lists would understate support (found by the eval harness on KawaiiPhysics, AI_LOG #10).
        runtime = [m for m in modules if not m.kind.startswith(_EDITOR_TYPES)]
        if runtime and all(m.platforms for m in runtime):
            platforms: list[str] = []
            for m in runtime:
                platforms += [p for p in m.platforms if p not in platforms]
            put("platforms", platforms)
        if data.get("Plugins"):
            deps = [str(p["Name"]) for p in data["Plugins"] if isinstance(p, dict) and p.get("Name")]
            put("dependencies", deps)

    def _apply_build_files(self, root: Path, plugin_dir: Path, profile: PluginProfile) -> None:
        source = plugin_dir / "Source"
        search_root = source if source.is_dir() else plugin_dir
        known = set(profile.module_names())
        deps = list(profile.dependencies)
        for build in walk(search_root, max_depth=4):
            if not build.name.endswith(".Build.cs"):
                continue
            name = build.name[: -len(".Build.cs")]
            # Guardrail: only trust a module name when the file sits in a folder of the same name.
            if build.parent.name != name or _is_test_module(name):
                continue
            if name not in known:
                profile.modules.append(Module(name=name))
                known.add(name)
                profile.sources.setdefault("modules", rel(root, build))
            text = read_text(build) or ""
            for m in _DEP_RE.finditer(text):
                for dep in _STR_RE.findall(m.group("body")):
                    if dep not in _TRIVIAL_DEPS and dep not in known and dep not in deps:
                        deps.append(dep)
        if deps != profile.dependencies:
            prior = profile.sources.get("dependencies")
            profile.dependencies = deps
            profile.sources["dependencies"] = ", ".join(filter(None, [prior, "Source/*/*.Build.cs"]))
