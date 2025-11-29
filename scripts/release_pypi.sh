#!/usr/bin/env bash
set -euo pipefail

# Vidurai v2.0.0 – PyPI Release Script
# REQUIREMENTS:
#   - TWINE_USERNAME and TWINE_PASSWORD or
#   - TWINE_USERNAME="__token__" and TWINE_PASSWORD="<pypi-api-token>"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[vidurai] Building SDK package (pyproject + build)..."
python -m build

echo "[vidurai] Checking artifacts with twine..."
twine check dist/*

echo "[vidurai] Uploading to PyPI..."
twine upload dist/*

echo "[vidurai] Done. Vidurai 2.0.0 should now be live on PyPI."
