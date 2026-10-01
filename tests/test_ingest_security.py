"""SECURITY.md upload/network items, automated."""

import io
import stat
import zipfile

import pytest

from storelistingkit.config import Limits
from storelistingkit.ingest import (
    IngestError,
    copy_local_folder,
    fetch_github_zip,
    parse_github_url,
    safe_extract_zip,
)


def make_zip(entries: dict[str, bytes], symlink: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, "/etc/passwd")
    return buf.getvalue()


def test_extracts_and_collapses_single_root(tmp_path):
    root = safe_extract_zip(make_zip({"repo-main/a.uplugin": b"{}", "repo-main/README.md": b"x"}), tmp_path)
    assert root.name == "repo-main" and (root / "a.uplugin").exists()


@pytest.mark.parametrize("name", ["../evil.txt", "/abs.txt", "a/../../evil.txt", "C:/win.txt", "..\\evil.txt"])
def test_rejects_path_traversal(tmp_path, name):
    with pytest.raises(IngestError):
        safe_extract_zip(make_zip({name: b"x"}), tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_rejects_symlinks(tmp_path):
    with pytest.raises(IngestError, match="Symlink"):
        safe_extract_zip(make_zip({"a.txt": b"x"}, symlink="link"), tmp_path)


def test_rejects_zip_bomb_by_ratio(tmp_path):
    with pytest.raises(IngestError, match="zip bomb"):
        safe_extract_zip(make_zip({"bomb.txt": b"\0" * 5_000_000}), tmp_path)


def test_rejects_oversized_unpacked_total(tmp_path):
    limits = Limits(max_unpacked_bytes=1000, max_ratio=10_000)
    with pytest.raises(IngestError):
        safe_extract_zip(make_zip({"a.bin": bytes(range(256)) * 10}), tmp_path, limits)


def test_rejects_too_many_files(tmp_path):
    limits = Limits(max_files=3)
    with pytest.raises(IngestError, match="entries"):
        safe_extract_zip(make_zip({f"f{i}": b"x" for i in range(5)}), tmp_path, limits)


def test_rejects_oversized_upload(tmp_path):
    with pytest.raises(IngestError, match="larger"):
        safe_extract_zip(b"0" * 2000, tmp_path, Limits(max_upload_bytes=1000))


def test_rejects_non_zip(tmp_path):
    with pytest.raises(IngestError, match="not a valid zip"):
        safe_extract_zip(b"not a zip", tmp_path)


@pytest.mark.parametrize("url", [
    "https://github.com/owner/repo", "https://github.com/owner/repo/", "https://github.com/o-1/r.e_p/tree/dev",
])
def test_github_url_accepted(url):
    owner, repo, _ = parse_github_url(url)
    assert owner and repo


@pytest.mark.parametrize("url", [
    "http://github.com/o/r", "https://evil.com/o/r", "https://github.com.evil.com/o/r",
    "https://github.com/o", "file:///etc/passwd", "https://github.com/o/r?x=@evil.com",
    "https://169.254.169.254/latest", "https://github.com/o/r/blob/main/x",
])
def test_github_url_rejected(url):
    with pytest.raises(IngestError):
        parse_github_url(url)


def test_fetch_refuses_bad_url_without_network():
    with pytest.raises(IngestError):
        fetch_github_zip("https://example.com/a/b")


def test_local_folder_copies_only_descriptors(tmp_path, fixtures):
    out = copy_local_folder(fixtures / "unreal_basic", tmp_path / "copy")
    assert (out / "QuickOutline" / "QuickOutline.uplugin").exists()
    assert not (out / "QuickOutline" / "Binaries").exists()


def test_local_folder_missing(tmp_path):
    with pytest.raises(IngestError, match="not found"):
        copy_local_folder(tmp_path / "missing", tmp_path / "copy")
