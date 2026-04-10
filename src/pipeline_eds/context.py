# src/pipeline_eds/context.py
from __future__ import annotations
from pathlib import Path
from dworshak_prompt import setup_dworshak_managers

DEFAULT_DWORSHAK_DIR = str(Path.home() / ".pipeline-eds")
dworshak_managers = setup_dworshak_managers(dir = globals().get("DEFAULT_DWORSHAK_DIR"))
dworshak_root = 
secret_mngr = dworshak_managers["secret"]
config_mngr = dworshak_managers["config"]
env_mngr = dworshak_managers["env"]
obtain_mngr = dworshak_managers["obtain"]