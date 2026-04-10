# src/pipeline_eds/context.py
from __future__ import annotations
from pathlib import Path
from dworshak_prompt import setup_dworshak_managers
from dworshak_prompt import Obtain, InterruptBehavior, PromptMode

DEFAULT_DWORSHAK_DIR = str(Path.home() / ".pipeline-eds")
dworshak_managers = setup_dworshak_managers(dir = globals().get("DEFAULT_DWORSHAK_DIR"))
dworshak_root_dir = dworshak_managers["root"] 
secret_mngr = dworshak_managers["secret"]
config_mngr = dworshak_managers["config"]
env_mngr = dworshak_managers["env"]
#obtain_mngr = dworshak_managers["obtain"]

# Add extra control features, compared to the standard obtain manager, but leverage the assigned pathing.
obtain_mngr = Obtain(
    config_path=config_mngr.path, 
    secret_path=secret_mngr.db_path, 
    interrupt_behavior=InterruptBehavior.EXIT,
    interface_priority=[PromptMode.WEB,PromptMode.GUI,PromptMode.CONSOLE]
    )