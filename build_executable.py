#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pyhabitat

from pipeline_eds.version_info import (
    get_package_name,
    get_package_version,
    get_python_version,
    form_dynamic_binary_name,
)

from pipeline_eds.system_info import SystemInfo


# =====
# CONFIG
# =====

PROJECT = get_package_name()
CLI_MAIN = Path.cwd() / "src/pipeline_eds/cli.py"
VERSION = get_package_version()

# ---- Dist layout (clean + predictable)
DIST_ROOT = Path("dist")
DIST_WHEELS = DIST_ROOT / "wheels"
DIST_ONEFILE = DIST_ROOT / "onefile"
DIST_ONEDIR = DIST_ROOT / "onedir"

# ---- Build isolation
BUILD_ROOT = Path("build")
BUILD_PYINSTALLER = BUILD_ROOT / "pyinstaller"
BUILD_ASSETS = Path("build_assets")

RC_TEMPLATE = BUILD_ASSETS / "version.rc.template"
RC_FILE = BUILD_PYINSTALLER / "version.rc"

ROOT = Path(__file__).resolve().parent

ASSETS = [
    (
        ROOT / "src/pipeline_eds/interface/web_gui/templates",
        "pipeline_eds/interface/web_gui/templates",
    ),
    (
        ROOT / "src/pipeline_eds/interface/web_gui/static",
        "pipeline_eds/interface/web_gui/static",
    ),
    (
        ROOT / "src/pipeline_eds/VERSION",
        "pipeline_eds",
    ),
]

for p in [
    DIST_ROOT,
    DIST_WHEELS,
    DIST_ONEFILE,
    DIST_ONEDIR,
    BUILD_ROOT,
    BUILD_PYINSTALLER,
    BUILD_ASSETS,
]:
    p.mkdir(parents=True, exist_ok=True)


# =====
# UTIL
# =====

def run(cmd: list[str], env: dict | None = None):
    print("\n$", " ".join(cmd))

    final_env = os.environ.copy()
    if env:
        final_env.update(env)

    subprocess.run(cmd, check=True, env=final_env)


def build_env() -> dict:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    if pyhabitat.on_termux():
        tmp = Path.home() / ".tmp"
        tmp.mkdir(exist_ok=True)
        env["TMPDIR"] = str(tmp)
        print(f"Using TMPDIR={tmp}")

    return env


# =====
# ASSETS
# =====

def verify_assets():

    missing = [src for src, _ in ASSETS if not src.exists()]

    if missing:
        raise RuntimeError(
            "Missing required assets:\n" + "\n".join(str(x) for x in missing)
        )

    print("Runtime assets verified")


# =====
# WINDOWS RC
# =====

def generate_rc_file(version: str):
    if not sys.platform.startswith("win"):
        return

    if not RC_TEMPLATE.exists():
        print("No RC template found, skipping.")
        return

    parts = version.split(".")
    while len(parts) < 4:
        parts.append("0")

    version_tuple = ", ".join(parts)

    content = RC_TEMPLATE.read_text(encoding="utf-8")
    content = content.replace("{{VERSION_STR}}", version)
    content = content.replace("{{VERSION_TUPLE}}", version_tuple)

    RC_FILE.write_text(content, encoding="utf-8")
    print(f"Generated RC: {RC_FILE}")


# =====
# WHEEL BUILD
# =====

def build_wheel() -> Path:
    env = build_env()

    run([
        "uv",
        "build",
        "--wheel",
        "--out-dir",
        str(DIST_WHEELS),
    ], env=env)

    wheels = sorted(
        DIST_WHEELS.glob("pipeline_eds-*.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not wheels:
        raise RuntimeError("No wheel produced")

    return wheels[0]


# =====
# EXECUTABLE BUILD
# =====

def get_pyinstaller():
    exe = Path(sys.executable).parent / "pyinstaller"
    if not exe.exists():
        raise RuntimeError(f"PyInstaller not found: {exe}")
    return exe
        
def build_executable(mode: str = "onefile"):
    verify_assets()

    wheel = build_wheel()

    sysinfo = SystemInfo()

    exe_name = form_dynamic_binary_name(
        PROJECT,
        VERSION,
        get_python_version(),
        sysinfo.get_os_tag(),
        sysinfo.get_arch(),
    )

    pyinstaller = get_pyinstaller()
    
    distpath = DIST_ONEFILE if mode == "onefile" else DIST_ONEDIR

    sep = ";" if sys.platform.startswith("win") else ":"
    cmd = [
        str(pyinstaller),
        str(CLI_MAIN),
        f"--name={exe_name}",
        f"--distpath={distpath}",
        f"--workpath={BUILD_PYINSTALLER}",
        f"--specpath={BUILD_PYINSTALLER}",
        "--clean",
        "--noconfirm",
    ]

    # mode switch
    cmd.append("--onefile" if mode == "onefile" else "--onedir")

    # include assets (critical for UI builds)
    
    cmd += [
        f"--add-data={src}{sep}{dest}"
        for src, dest in ASSETS
    ]
    # Windows RC
    if sys.platform.startswith("win") and RC_FILE.exists():
        cmd.append(f"--version-file={RC_FILE}")

    env = build_env()

    run(cmd, env=env)

    # =====
    # OUTPUT
    # =====

    ext = ".exe" if sys.platform.startswith("win") else ""

    artifact = (
        DIST_ONEFILE / f"{exe_name}{ext}"
        if mode == "onefile"
        else DIST_ONEDIR / exe_name
    )

    print("\nBuild complete:")
    print(artifact.resolve())

    # cleanup
    RC_FILE.unlink(missing_ok=True)


# =====
# MAIN
# =====
if __name__ == "__main__":
    generate_rc_file(VERSION)

    mode = "onefile"

    if "--onedir" in sys.argv:
        mode = "onedir"

    build_executable(mode=mode)
