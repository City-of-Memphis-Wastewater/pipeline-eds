#!/usr/bin/env bash
set -euo pipefail

# uv sync --extra kivy --group dev --extra buildozer

# Run from packaging/kivy directory
cd "$(dirname "$0")/../packaging/buildozer"

uv run buildozer android debug \
  app.source.dir="$(pwd)/../../src/frontend_kivy" \
  buildozer.build_dir="$(pwd)/../../build/buildozer" \
  buildozer.bin_dir="$(pwd)/../../dist/buildozer"
