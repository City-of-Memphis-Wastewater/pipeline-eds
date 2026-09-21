# packaging/kivy/main.spec
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SPEC_DIR = Path(SPEC).resolve().parent
REPO_ROOT = SPEC_DIR.parents[1]
SRC_DIR = REPO_ROOT / "src"
ENTRY_POINT = SRC_DIR / "pipeline_eds" / "__main__.py"

# Safely collect Kivy submodules
kivy_hiddenimports = collect_submodules(
    "kivy",
    filter=lambda name: not name.startswith("kivy.garden"),
)

# Collect required data files for Kivy
kivy_datas = collect_data_files("kivy")

a = Analysis(
    [str(ENTRY_POINT)],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[
        (str(SRC_DIR / "frontend_kivy" / "*.kv"), "frontend_kivy"),
        (str(SRC_DIR / "pipeline_eds" / "data"), "pipeline_eds/data"),
    ] + kivy_datas,
    hiddenimports=[
        "pipeline_eds",
        "pipeline_eds.cli",
        "frontend_kivy",
        "frontend_kivy.app",
        "frontend_kivy.screens",
        "frontend_kivy.widgets",
    ] + collect_submodules("pipeline_eds") + kivy_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["kivy.garden"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pipeline-eds",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pipeline-eds",
)
