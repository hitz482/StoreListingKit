"""Repo ingestion: zip upload, public GitHub URL, or a local folder.

HUMAN GATE (docs/REVIEW_NOTES.md). Protections:
- zip: total compressed size cap, total uncompressed cap (from headers *and* enforced while streaming),
  file-count cap, per-entry compression-ratio cap, path traversal (absolute paths, '..', drive letters),
  symlink entries rejected, encrypted entries rejected.
- URL: only https://github.com/<owner>/<repo>[/tree/<ref>]; download from codeload.github.com only;
  redirects are not followed off that host; size cap while streaming; timeout.
- local folder: must be an existing directory; read-only parsing, nothing executed.
"""

from __future__ import annotations

import io
import re
import shutil
import stat
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from .config import LIMITS, Limits


class IngestError(ValueError):
    """User-facing ingestion failure. The message is safe to show in the UI."""


_GITHUB_URL = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/(?P<repo>[A-Za-z0-9._-]{1,100})"
    r"(?:/tree/(?P<ref>[A-Za-z0-9._/-]{1,200}))?/?$"
)


def _safe_member_path(name: str) -> PurePosixPath | None:
    """Return a safe relative path for a zip member, or None if the member must be rejected."""
    name = name.replace("\\", "/")
    if not name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        return None
    parts = PurePosixPath(name).parts
    if any(p in ("..", "") for p in parts):
        return None
    return PurePosixPath(*parts) if parts else None


def safe_extract_zip(data: bytes | Path, dest: Path, limits: Limits = LIMITS) -> Path:
    """Extract a zip into ``dest`` safely and return the repo root (single top folder collapsed)."""
    if isinstance(data, Path):
        size = data.stat().st_size
        source: io.BufferedIOBase | Path = data
    else:
        size = len(data)
        source = io.BytesIO(data)
    if size > limits.max_upload_bytes:
        raise IngestError(f"Zip is larger than {limits.max_upload_bytes // (1024 * 1024)} MB.")
    try:
        zf = zipfile.ZipFile(source)
    except zipfile.BadZipFile as exc:
        raise IngestError("File is not a valid zip archive.") from exc

    with zf:
        infos = zf.infolist()
        if len(infos) > limits.max_files:
            raise IngestError(f"Zip has more than {limits.max_files} entries.")
        declared = sum(i.file_size for i in infos)
        if declared > limits.max_unpacked_bytes:
            raise IngestError("Zip would unpack to more than the allowed size (possible zip bomb).")

        dest.mkdir(parents=True, exist_ok=True)
        dest_resolved = dest.resolve()
        written = 0
        for info in infos:
            rel_path = _safe_member_path(info.filename)
            if rel_path is None:
                raise IngestError(f"Unsafe path in zip: {info.filename!r}")
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise IngestError(f"Symlinks are not allowed in uploads: {info.filename!r}")
            if info.flag_bits & 0x1:
                raise IngestError("Encrypted zip entries are not supported.")
            if info.compress_size and info.file_size / max(info.compress_size, 1) > limits.max_ratio:
                raise IngestError("Suspicious compression ratio (possible zip bomb).")

            target = (dest / rel_path).resolve()
            if not target.is_relative_to(dest_resolved):
                raise IngestError(f"Unsafe path in zip: {info.filename!r}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                while chunk := src.read(64 * 1024):
                    written += len(chunk)
                    # Headers can lie; enforce the cap on actual bytes.
                    if written > limits.max_unpacked_bytes:
                        raise IngestError("Zip unpacks to more than the allowed size (possible zip bomb).")
                    out.write(chunk)
    return collapse_single_root(dest)


def collapse_single_root(dest: Path) -> Path:
    entries = [p for p in dest.iterdir() if p.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return dest


def parse_github_url(url: str) -> tuple[str, str, str | None]:
    m = _GITHUB_URL.match(url.strip())
    if not m:
        raise IngestError("Only public GitHub repository URLs are supported, e.g. https://github.com/owner/repo")
    repo = m.group("repo").removesuffix(".git")
    return m.group("owner"), repo, m.group("ref")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802 - stdlib API
        if not newurl.startswith("https://codeload.github.com/"):
            raise IngestError("GitHub redirected to an unexpected host; aborting.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_github_zip(url: str, limits: Limits = LIMITS, timeout: float = 30.0) -> bytes:
    owner, repo, ref = parse_github_url(url)
    ref_path = f"refs/heads/{ref}" if ref else "HEAD"
    download = f"https://codeload.github.com/{owner}/{repo}/zip/{ref_path}"
    opener = urllib.request.build_opener(_NoRedirect)
    # Scheme and host are fixed above (https://codeload.github.com), so S310 does not apply.
    req = urllib.request.Request(download, headers={"User-Agent": "StoreListingKit/0.1"})  # noqa: S310
    try:
        with opener.open(req, timeout=timeout) as resp:
            buf = io.BytesIO()
            while chunk := resp.read(256 * 1024):
                buf.write(chunk)
                if buf.tell() > limits.max_upload_bytes:
                    raise IngestError("Repository archive is larger than the allowed upload size.")
            return buf.getvalue()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise IngestError("Repository or branch not found (is it public?).") from exc
        raise IngestError(f"GitHub returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise IngestError("Could not reach GitHub. Check your internet connection.") from exc


def copy_local_folder(src: str | Path, dest: Path, limits: Limits = LIMITS) -> Path:
    """Snapshot a local plugin folder (e.g. from the UE/Unity bridge) into the workspace.

    We copy only text-like descriptor/source files we parse, so huge Content/ folders are skipped.
    """
    root = Path(src).expanduser()
    if not root.is_dir():
        raise IngestError(f"Folder not found: {root}")
    wanted = {".uplugin", ".cs", ".json", ".asmdef", ".md", ".txt", ".ini", ".rst", ""}
    count = total = 0
    from .adapters.base import IGNORED_DIRS

    for path in sorted(root.rglob("*")):
        relp = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relp.parts) or path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in wanted or path.stat().st_size > 1_000_000:
            continue
        if relp.parts and relp.parts[0] == "ProjectSettings" and path.name != "ProjectVersion.txt":
            continue
        count += 1
        total += path.stat().st_size
        if count > limits.max_files or total > limits.max_unpacked_bytes:
            raise IngestError("Folder is too large to scan.")
        target = dest / relp
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    dest.mkdir(parents=True, exist_ok=True)
    return dest
