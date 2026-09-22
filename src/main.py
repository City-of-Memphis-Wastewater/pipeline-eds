# src/main.py
"""Android entry point for python-for-android / buildozer."""
import sys
from pathlib import Path

# Point to project root vendor directory (../vendor)
vendor_dir = Path(__file__).resolve().parent.parent / "vendor"
if vendor_dir.exists():
    sys.path.insert(0, str(vendor_dir))

from frontend_kivy.app import main

if __name__ == "__main__":
    main()
