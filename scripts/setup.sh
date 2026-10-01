#!/usr/bin/env bash
# One-command local setup (macOS/Linux): ./scripts/setup.sh
set -euo pipefail
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
echo "Done. Start the app with: .venv/bin/python -m storelistingkit"
