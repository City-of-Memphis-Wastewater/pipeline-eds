#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_DIR="${PROJECT_ROOT}/vendor/site-packages"  # or vendor_for_buildozer

echo "==> Auditing build dependencies..."

# 1. Check if vendor directory exists and has contents
if [ ! -d "${VENDOR_DIR}" ] || [ -z "$(ls -A "${VENDOR_DIR}" 2>/dev/null)" ]; then
    echo "ERROR: Vendored packages directory is missing or empty at:"
    echo "       ${VENDOR_DIR}"
    echo ""
    echo "Please populate vendored packages before building:"
    echo "       uv run mbu vendor site-packages"
    echo "       or "
    echo "       uv pip install ...  --target ./vendor/site-packages/" 
    exit 1
fi

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
#  --target ./vendor/site-packages/


# Navigate to spec directory
cd "${REPO_ROOT}/packaging/buildozer"

# Execute Buildozer via uv
uv run buildozer android debug

