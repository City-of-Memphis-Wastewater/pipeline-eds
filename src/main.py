# src/main.py
"""Android entry point for python-for-android / buildozer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "suds_vendor"))

from frontend_kivy.app import main

if __name__ == "__main__":
    main()
