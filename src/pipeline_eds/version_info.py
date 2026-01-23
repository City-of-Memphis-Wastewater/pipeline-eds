# src/pipeline_eds/version_info.py
from __future__ import annotations

import sys
from pathlib import Path

from pipeline_eds._version import __version__  # ← single source of truth
from pipeline_eds.system_info import SystemInfo

# Package metadata (static or derived)
PIP_PACKAGE_NAME = "pipeline-eds"
PACKAGE_VERSION = __version__  # Use the real version directly

def get_package_version() -> str:
    """Return the current package version."""
    return PACKAGE_VERSION

def get_package_name() -> str:
    """Return the package distribution name."""
    return PIP_PACKAGE_NAME

def get_python_version() -> str:
    """Return Python major.minor version tag (e.g. 'py312')."""
    py_major = sys.version_info.major
    py_minor = sys.version_info.minor
    return f"py{py_major}{py_minor}"

def form_dynamic_binary_name(
    package_name: str,
    package_version: str,
    py_version: str,
    os_tag: str,
    arch: str
) -> str:
    """Form a hyphenated binary/artifact name for distribution."""
    return f"{package_name}-{package_version}-{py_version}-{os_tag}-{arch}"

if __name__ == "__main__":
    package_name = get_package_name()
    package_version = get_package_version()
    py_version = get_python_version()

    sysinfo = SystemInfo()
    os_tag = sysinfo.get_os_tag()
    architecture = sysinfo.get_arch()

    bin_name = form_dynamic_binary_name(
        package_name, package_version, py_version, os_tag, architecture
    )
    print(f"bin_name = {bin_name}")

