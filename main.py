# main.py
"""Android entry point for python-for-android / buildozer."""
from __future__ import annotations
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
VENDOR_DIR = BASE_DIR / "vendor_for_buildozer"

for directory in (BASE_DIR, SRC_DIR, VENDOR_DIR):
    if directory.exists():
        dir_str = str(directory)
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)

from frontend_kivy.app import launch_kivy_app

if __name__ == "__main__":
    launch_kivy_app()
