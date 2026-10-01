from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true", help="Rewrite golden files from current output.")


@pytest.fixture
def update_golden(request) -> bool:
    return request.config.getoption("--update-golden")


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SLK_STORE_SPECS", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    from storelistingkit import config

    config.KEYS.set_session_key(None)
