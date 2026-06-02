#!/usr/bin/env python3
"""
build_pyz.py
=============

Build portable pipeline-eds executables using shiv.

Goals:
- simple
- reproducible
- Termux-safe
- no baked .pyc
- wheel-first workflow
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pyhabitat

from pipeline_eds.version_info import (
    get_package_name,
    __version__,
)

# ------
# Config
# ------

PROJECT = get_package_name()
VERSION = __version__

ENTRY = "pipeline_eds.cli:app"

DIST = Path("dist")
DIST.mkdir(exist_ok=True)

DIST_ROOT = Path("dist")
DIST_ZIPAPP = DIST_ROOT / "zipapp"
DIST_WHEELS = DIST_ROOT / "wheels"

BUILD_ROOT = Path("build") / "zipapp"

for d in [DIST_ROOT, DIST_ZIPAPP, DIST_WHEELS]:
    d.mkdir(parents=True, exist_ok=True)

# ------
# Helpers
# ------

def run(cmd: list[str], env: dict | None = None):
    print("\n$", " ".join(cmd))

    final_env = os.environ.copy()

    if env:
        final_env.update(env)

    subprocess.run(
        cmd,
        check=True,
        env=final_env,
    )


def platform_tag() -> str:
    """
    Example:
        android-aarch64
        linux-x86_64
        windows-amd64
    """

    if pyhabitat.on_termux():
        return "android-aarch64"

    info = pyhabitat.SystemInfo()

    return f"{info.system.lower()}-{info.architecture.lower()}"


def build_env() -> dict:
    """
    Build environment tweaks.

    Important for:
    - Termux TMPDIR
    - disabling pyc generation
    """

    env = os.environ.copy()

    env["PYTHONDONTWRITEBYTECODE"] = "1"

    if pyhabitat.on_termux():
        tmp = Path.home() / ".tmp"
        tmp.mkdir(exist_ok=True)

        env["TMPDIR"] = str(tmp)

        print(f"Using TMPDIR={tmp}")

    return env


# ------
# Wheel
# ------

def build_wheel():
    env = build_env()

    run(
        [
            "uv",
            "build",
            "--wheel",
            "--out-dir",
            str(DIST_WHEELS),
        ],
        env=env,
    )
    
    wheels = sorted(
        DIST_WHEELS.glob("pipeline_eds-*.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not wheels:
        raise RuntimeError("No wheel produced")

    return wheels[0]


def latest_wheel() -> Path:
    wheels = sorted(
        DIST.glob("pipeline_eds-*.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not wheels:
        raise RuntimeError("No wheel produced")

    return wheels[0]


# ------
# Asset Verification
# ------

def verify_assets():
    """
    Ensure critical runtime assets exist before build.
    """ 
    required = [
        Path("src/pipeline_eds/interface/web_gui/templates"),
        Path("src/pipeline_eds/interface/web_gui/static"),
        Path("src/pipeline_eds/data/sensors.db"),
        Path("src/pipeline_eds/VERSION"),
    ]

    missing = [p for p in required if not p.exists()]

    if missing:
        raise RuntimeError(
            "Missing required assets:\n"
            + "\n".join(str(x) for x in missing)
        )

    print("Runtime assets verified")


# ------
# Build PYZ
# ------

def build_pyz():

    verify_assets()

    wheel = build_wheel()

    pyz_name = (
        f"{PROJECT}-"
        f"{VERSION}-"
        f"{platform_tag()}.pyz"
    )

    output = DIST_ZIPAPP / pyz_name

    if output.exists():
        output.unlink()

    env = build_env()

    run(
        [
            "shiv",
            str(wheel),
            "-o",
            str(output),
            "-e",
            ENTRY,
            "-p",
            pyhabitat.get_interp_shebang(),
            "--compressed",
            "--no-cache",
        ],
        env=env,
    )

    if os.name != "nt":
        output.chmod(0o755)

    print(f"\nBuilt: {output.resolve()}")


# ------
# Main
# ------

if __name__ == "__main__":
    build_pyz()
