# src/pipeline_eds/__buildozer_entry__.py
"""Buildozer / Android runtime orchestration entry point."""
from __future__ import annotations

import os
import sys
from pathlib import Path

def bootstrap_environment_kivy() -> None:
    """Configure paths and environment variables before Kivy initializes."""
    # Root main.py is 2 levels up from src/pipeline_eds/
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    src_dir = base_dir / "src"
    vendor_dir = base_dir / "vendor" / "site-packages"

    os.environ.setdefault("KIVY_HOME", str(base_dir / ".kivy"))
    os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

    for directory in (base_dir, src_dir, vendor_dir):
        if directory.exists():
            dir_str = str(directory)
            if dir_str not in sys.path:
                sys.path.insert(0, dir_str)

def bootstrap_environment() -> None:
    """Configure paths for web view of the webapp."""
    # Root main.py is 2 levels up from src/pipeline_eds/
    base_dir = Path(__file__).resolve().parent.parent.parent
    src_dir = base_dir / "src"
    vendor_dir = base_dir / "vendor" / "site-packages"

    for directory in (base_dir, src_dir, vendor_dir):
        if directory.exists():
            dir_str = str(directory)
            if dir_str not in sys.path:
                sys.path.insert(0, dir_str)

def main() -> None:
    """Orchestrates application startup for Buildozer."""
    bootstrap_environment()

    #from pipeline_eds.kivy.app import launch_kivy_app
    #launch_kivy_app()
    from .server.trend_server_eds import launch_server_for_web_interface_eds_trend
    launch_server_for_web_interface_eds_trend()

if __name__ == "__main__":
    main()
