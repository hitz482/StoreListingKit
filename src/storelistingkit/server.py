"""Local HTTP API + static UI. HUMAN GATE for auth/key code (docs/REVIEW_NOTES.md).

Security model (ADR 0006): bound to 127.0.0.1, per-launch random token required on /api/*,
Host header allow-list against DNS rebinding, per-token generation rate limit.
"""

from __future__ import annotations

import hmac
import logging
import secrets
import shutil
import tempfile
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from . import __version__, config, engines
from .adapters import detect_engine, extract_profile
from .exporter import build_zip, slug
from .generator import ClaudeGenerator, GenerationError, ListingGenerator, TemplateGenerator
from .images import ImageError, build_store_images, load_image
from .ingest import IngestError, copy_local_folder, fetch_github_zip, safe_extract_zip
from .models import ENGINE_STORES, ListingKit, PluginProfile, StoreCopy, StoreId
from .stores import specs, validate_copy, validate_images

log = logging.getLogger(__name__)


@dataclass
class Project:
    id: str
    dir: Path
    profile: PluginProfile
    engine_confidence: float
    origin: str
    screenshots: list[str] = field(default_factory=list)
    kit: ListingKit | None = None


@dataclass
class Job:
    id: str
    project_id: str
    stores: list[StoreId]
    state: Literal["running", "done", "error"] = "running"
    steps: dict[str, str] = field(default_factory=dict)  # store -> pending/running/done/error
    errors: dict[str, list[str]] = field(default_factory=dict)
    started: float = field(default_factory=time.time)


class AppState:
    def __init__(self, token: str, port: int, workspace: Path | None = None,
                 generator_factory=None) -> None:
        self.token = token
        self.port = port
        self.workspace = workspace or Path(tempfile.mkdtemp(prefix="slk-"))
        self.projects: dict[str, Project] = {}
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.rate: deque[float] = deque()
        self.generator_factory = generator_factory
        self.startup_project: str | None = None

    def cleanup(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)


class UrlSource(BaseModel):
    url: str | None = None
    path: str | None = None


class KeyBody(BaseModel):
    key: str


class GenerateBody(BaseModel):
    stores: list[StoreId] | None = None
    mode: Literal["auto", "claude", "template"] = "auto"


class BridgeBody(BaseModel):
    project_dir: str


def create_app(state: AppState) -> FastAPI:
    app = FastAPI(title="Store Listing Kit", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.slk = state
    allowed_hosts = {f"127.0.0.1:{state.port}", f"localhost:{state.port}", "testserver"}

    @app.middleware("http")
    async def host_guard(request: Request, call_next):
        if request.headers.get("host", "") not in allowed_hosts:
            return JSONResponse({"detail": "Forbidden host"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'"
        )
        return response

    def require_token(
        x_slk_token: Annotated[str | None, Header()] = None,
        t: Annotated[str | None, Query()] = None,
    ) -> None:
        supplied = x_slk_token or t or ""
        if not hmac.compare_digest(supplied.encode(), state.token.encode()):
            raise HTTPException(status_code=401, detail="Missing or invalid session token.")

    auth = [Depends(require_token)]

    def get_project(pid: str) -> Project:
        p = state.projects.get(pid)
        if p is None:
            raise HTTPException(404, "Project not found.")
        return p

    def project_view(p: Project) -> dict:
        return {
            "id": p.id,
            "origin": p.origin,
            "profile": p.profile.model_dump(),
            "engine_confidence": p.engine_confidence,
            "stores": [s.value for s in ENGINE_STORES[p.profile.engine]],
            "screenshots": p.screenshots,
            "kit": p.kit.model_dump(mode="json") if p.kit else None,
        }

    # ------------------------------------------------------------------ status & key

    @app.get("/api/status", dependencies=auth)
    def status() -> dict:
        return {
            "version": __version__,
            "key_source": config.KEYS.source(),
            "model": config.model(),
            "specs": specs(),
            "startup_project": state.startup_project,
        }

    @app.post("/api/key", dependencies=auth)
    def set_key(body: KeyBody) -> dict:
        key = body.key.strip()
        if not key.startswith("sk-ant-") or len(key) > 300:
            raise HTTPException(400, "That does not look like an Anthropic API key.")
        config.KEYS.set_session_key(key)
        return {"key_source": config.KEYS.source()}

    @app.delete("/api/key", dependencies=auth)
    def clear_key() -> dict:
        config.KEYS.set_session_key(None)
        return {"key_source": config.KEYS.source()}

    # ------------------------------------------------------------------ engines / bridges

    @app.get("/api/engines", dependencies=auth)
    def list_engines() -> dict:
        return {"installs": [e.model_dump() for e in engines.find_installs()]}

    @app.post("/api/engines/bridge", dependencies=auth)
    def bridge(body: BridgeBody) -> dict:
        try:
            return engines.install_bridge(body.project_dir)
        except (engines.BridgeError, OSError) as exc:
            raise HTTPException(400, str(exc)) from exc

    # ------------------------------------------------------------------ projects

    def new_project(root_fn, origin: str) -> Project:
        pid = uuid.uuid4().hex[:12]
        pdir = state.workspace / pid
        repo_dir = pdir / "repo"
        repo_dir.mkdir(parents=True)
        root = root_fn(repo_dir)
        engine, conf = detect_engine(root)
        profile = extract_profile(root)
        p = Project(id=pid, dir=pdir, profile=profile, engine_confidence=conf, origin=origin)
        (pdir / "screenshots").mkdir()
        with state.lock:
            state.projects[pid] = p
        log.info("project %s created from %s (engine=%s)", pid, origin, engine)
        return p

    @app.post("/api/projects/upload", dependencies=auth)
    async def upload_project(file: Annotated[UploadFile, File()]) -> dict:
        data = await file.read(config.LIMITS.max_upload_bytes + 1)
        try:
            p = new_project(lambda d: safe_extract_zip(data, d), f"zip:{file.filename}")
        except IngestError as exc:
            raise HTTPException(400, str(exc)) from exc
        return project_view(p)

    @app.post("/api/projects/source", dependencies=auth)
    def source_project(body: UrlSource) -> dict:
        try:
            if body.url:
                data = fetch_github_zip(body.url)
                p = new_project(lambda d: safe_extract_zip(data, d), body.url)
            elif body.path:
                p = new_project(lambda d: copy_local_folder(body.path, d), f"folder:{body.path}")
            else:
                raise IngestError("Provide a GitHub URL or a local folder path.")
        except IngestError as exc:
            raise HTTPException(400, str(exc)) from exc
        return project_view(p)

    @app.get("/api/projects/{pid}", dependencies=auth)
    def read_project(pid: str) -> dict:
        return project_view(get_project(pid))

    @app.put("/api/projects/{pid}/profile", dependencies=auth)
    def update_profile(pid: str, profile: PluginProfile) -> dict:
        p = get_project(pid)
        # Keep provenance from extraction; mark user-edited fields.
        old = p.profile
        for fname in PluginProfile.model_fields:
            if fname in {"sources", "warnings"}:
                continue
            if getattr(profile, fname) != getattr(old, fname):
                profile.sources[fname] = "edited by user"
        profile.warnings = old.warnings
        p.profile = profile
        return project_view(p)

    # ------------------------------------------------------------------ screenshots

    @app.post("/api/projects/{pid}/screenshots", dependencies=auth)
    async def add_screenshots(pid: str, files: Annotated[list[UploadFile], File()]) -> dict:
        p = get_project(pid)
        errors: list[str] = []
        for f in files:
            if len(p.screenshots) >= config.LIMITS.max_images:
                errors.append(f"Maximum {config.LIMITS.max_images} screenshots.")
                break
            data = await f.read(config.LIMITS.max_image_bytes + 1)
            ext = Path(f.filename or "").suffix.lower()
            if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
                errors.append(f"{f.filename}: only PNG, JPEG or WebP.")
                continue
            name = f"{len(p.screenshots) + 1:02d}_{uuid.uuid4().hex[:6]}{ext}"
            target = p.dir / "screenshots" / name
            target.write_bytes(data[: config.LIMITS.max_image_bytes + 1])
            try:
                load_image(target)
            except ImageError as exc:
                target.unlink(missing_ok=True)
                errors.append(f"{f.filename}: {exc}".replace(f"{name}: ", ""))
                continue
            p.screenshots.append(name)
        return {**project_view(p), "errors": errors}

    @app.delete("/api/projects/{pid}/screenshots/{name}", dependencies=auth)
    def delete_screenshot(pid: str, name: str) -> dict:
        p = get_project(pid)
        if name not in p.screenshots:
            raise HTTPException(404, "Screenshot not found.")
        p.screenshots.remove(name)
        (p.dir / "screenshots" / name).unlink(missing_ok=True)
        return project_view(p)

    @app.post("/api/projects/{pid}/screenshots/order", dependencies=auth)
    def order_screenshots(pid: str, names: list[str]) -> dict:
        p = get_project(pid)
        if sorted(names) != sorted(p.screenshots):
            raise HTTPException(400, "Order must contain exactly the current screenshots.")
        p.screenshots = names
        return project_view(p)

    @app.get("/api/projects/{pid}/screenshots/{name}", dependencies=auth)
    def get_screenshot(pid: str, name: str) -> FileResponse:
        p = get_project(pid)
        if name not in p.screenshots:
            raise HTTPException(404, "Screenshot not found.")
        return FileResponse(p.dir / "screenshots" / name)

    @app.get("/api/projects/{pid}/images/{store}/{name}", dependencies=auth)
    def get_image(pid: str, store: StoreId, name: str) -> FileResponse:
        p = get_project(pid)
        if not p.kit or not any(i.store == store and i.filename == name for i in p.kit.images):
            raise HTTPException(404, "Image not found.")
        return FileResponse(p.dir / "images" / store.value / name)

    # ------------------------------------------------------------------ generation

    def pick_generator(mode: str) -> ListingGenerator:
        if state.generator_factory:
            return state.generator_factory(mode)
        if mode == "template":
            return TemplateGenerator()
        if mode == "claude" and not config.KEYS.get():
            raise HTTPException(400, "Add an Anthropic API key or choose the offline template.")
        return ClaudeGenerator() if config.KEYS.get() else TemplateGenerator()

    def check_rate() -> None:
        now = time.time()
        with state.lock:
            while state.rate and now - state.rate[0] > 60:
                state.rate.popleft()
            if len(state.rate) >= config.LIMITS.generate_per_minute:
                raise HTTPException(429, "Too many generations; wait a minute.")
            state.rate.append(now)

    def run_job(job: Job, p: Project, gen: ListingGenerator) -> None:
        kit = ListingKit(profile=p.profile.model_copy(deep=True))
        p.kit = kit
        shots = [p.dir / "screenshots" / n for n in p.screenshots]
        for store in job.stores:
            job.steps[store.value] = "running"
            try:
                images = build_store_images(store, shots, kit.profile.title, p.dir / "images" / store.value)
                kit.images.extend(images)
                copy = gen.generate(kit.profile, store)
                kit.copies[store] = copy
                kit.issues.extend(validate_copy(copy))
                kit.issues.extend(validate_images(store, images, len(shots)))
                job.steps[store.value] = "done"
            except GenerationError as exc:
                job.steps[store.value] = "error"
                job.errors[store.value] = [str(exc), *exc.problems]
            except ImageError as exc:
                job.steps[store.value] = "error"
                job.errors[store.value] = [str(exc)]
            except Exception:  # noqa: BLE001 - never leak internals to the UI
                log.exception("generation failed")
                job.steps[store.value] = "error"
                job.errors[store.value] = ["Unexpected error; see the console window for details."]
        job.state = "error" if job.errors and not kit.copies else "done"

    @app.post("/api/projects/{pid}/generate", dependencies=auth)
    def generate(pid: str, body: GenerateBody) -> dict:
        p = get_project(pid)
        stores = body.stores or ENGINE_STORES[p.profile.engine]
        gen = pick_generator(body.mode)
        check_rate()
        job = Job(id=uuid.uuid4().hex[:12], project_id=pid, stores=list(stores))
        job.steps = {s.value: "pending" for s in stores}
        state.jobs[job.id] = job
        threading.Thread(target=run_job, args=(job, p, gen), daemon=True).start()
        return {"job_id": job.id, "generator": gen.name}

    @app.get("/api/jobs/{jid}", dependencies=auth)
    def job_status(jid: str) -> dict:
        job = state.jobs.get(jid)
        if not job:
            raise HTTPException(404, "Job not found.")
        p = state.projects[job.project_id]
        return {
            "state": job.state,
            "steps": job.steps,
            "errors": job.errors,
            "elapsed": round(time.time() - job.started, 1),
            "kit": p.kit.model_dump(mode="json") if p.kit else None,
        }

    @app.put("/api/projects/{pid}/copies/{store}", dependencies=auth)
    def edit_copy(pid: str, store: StoreId, body: dict) -> dict:
        p = get_project(pid)
        if not p.kit or store not in p.kit.copies:
            raise HTTPException(404, "Generate first.")
        current = p.kit.copies[store]
        allowed = {"title", "short_description", "long_description", "features", "tags", "technical_details"}
        try:
            updated = StoreCopy.model_validate(
                {**current.model_dump(), **{k: v for k, v in body.items() if k in allowed}}
            )
        except ValidationError as exc:
            raise HTTPException(400, "Invalid listing fields.") from exc
        if updated != current:
            updated.generated_by = current.generated_by.split("+")[0] + "+edited"
        p.kit.copies[store] = updated
        p.kit.issues = [i for i in p.kit.issues if i.store != store or i.field.startswith("image:")]
        p.kit.issues.extend(validate_copy(updated))
        return project_view(p)

    @app.get("/api/projects/{pid}/export", dependencies=auth)
    def export(pid: str) -> Response:
        p = get_project(pid)
        if not p.kit or not p.kit.copies:
            raise HTTPException(400, "Nothing to export yet.")
        data = build_zip(p.kit, p.dir / "images")
        name = f"{slug(p.profile.title)}-listing-kit.zip"
        return Response(data, media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    # ------------------------------------------------------------------ static UI

    static_dir = Path(str(resources.files("storelistingkit").joinpath("static")))

    @app.get("/", response_class=HTMLResponse)
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app


def preload(state: AppState, source: str | None, screenshots: str | None) -> None:
    """Create a project from a local folder (used by the editor bridges via CLI flags)."""
    if not source:
        return
    pid = uuid.uuid4().hex[:12]
    pdir = state.workspace / pid
    root = copy_local_folder(source, pdir / "repo")
    engine, conf = detect_engine(root)
    p = Project(id=pid, dir=pdir, profile=extract_profile(root), engine_confidence=conf, origin=f"folder:{source}")
    (pdir / "screenshots").mkdir(parents=True)
    if screenshots and Path(screenshots).is_dir():
        for src in sorted(Path(screenshots).iterdir()):
            if len(p.screenshots) >= config.LIMITS.max_images:
                break
            if src.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                name = f"{len(p.screenshots) + 1:02d}_{uuid.uuid4().hex[:6]}{src.suffix.lower()}"
                shutil.copyfile(src, pdir / "screenshots" / name)
                try:
                    load_image(pdir / "screenshots" / name)
                    p.screenshots.append(name)
                except ImageError:
                    (pdir / "screenshots" / name).unlink(missing_ok=True)
    state.projects[pid] = p
    state.startup_project = pid


def new_token() -> str:
    return secrets.token_urlsafe(32)
