# main.py
"""Android entry point for python-for-android / buildozer."""
import sys
from pathlib import Path

# Ensure the root directory and src/ directory are on sys.path inside Android
# Base directory where main.py lives
BASE_DIR = Path(__file__).resolve().parent

# Directories to add to sys.path
SRC_DIR = BASE_DIR / "src"
VENDOR_DIR = BASE_DIR / "vendor_for_buildozer"

for directory in (BASE_DIR, SRC_DIR, VENDOR_DIR):
    if directory.exists():
        dir_str = str(directory)
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)

from frontend_kivy.app import main

if __name__ == "__main__":
    main()
