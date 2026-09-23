#!/usr/bin/env bash
set -euo pipefail


# uv sync --extra kivy --group dev --extra buildozer


# Determine repository root relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Ensure vendor dependencies are updated if enabled
# uv pip install --target "${REPO_ROOT}/vendor_for_buildozer" -r "${REPO_ROOT}/requirements-buildozer.txt"


#uv pip install \
#  backports.tarfile \
#  certifi \
#  chardet \
#  charset_normalizer \
#  idna \
#  openpyxl \
#  pendulum \
#  requests \
#  suds-py3 \
#  tzdata \
#  urllib3 \
#  --target ./build/vendor_for_buildozer


# Navigate to spec directory
cd "${REPO_ROOT}/packaging/buildozer"

# Execute Buildozer via uv
uv run buildozer android debug

