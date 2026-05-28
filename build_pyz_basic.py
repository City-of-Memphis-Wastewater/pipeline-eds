#!/usr/bin/env python3

from pathlib import Path
import subprocess
import os
import sys
import pyhabitat

PROJECT = "pipeline-eds"
ENTRY = "pipeline_eds.cli:app"

DIST = Path("dist")
DIST.mkdir(exist_ok=True)

def run(cmd):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)

def build():
    run([
        "uv",
        "build",
        "--wheel",
        "--out-dir",
        str(DIST),
    ])

def latest_wheel():
    wheels = sorted(
        DIST.glob("pipeline_eds-*.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return wheels[0]

def build_pyz():
    build()

    wheel = latest_wheel()

    out = DIST / "pipeline-eds.pyz"

    run([
        "shiv",
        str(wheel),
        "-o",
        str(out),
        "-e",
        ENTRY,
        "-p",
        pyhabitat.get_interp_shebang(),
        "--compressed",
        "--no-cache",
    ])

    out.chmod(0o755)

    print(f"Built: {out}")

if __name__ == "__main__":
    build_pyz()
