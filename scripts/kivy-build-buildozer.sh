#!/usr/bin/env bash
set -euo pipefail

# Run from packaging/kivy directory
cd "$(dirname "$0")/../packaging/buildozer"

buildozer android debug \
  app.source.dir="$(pwd)/../../src/frontend_kivy" \
  buildozer.build_dir="$(pwd)/../../build/buildozer" \
  buildozer.bin_dir="$(pwd)/../../dist/buildozer"
