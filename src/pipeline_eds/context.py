# src/pipeline_eds/context.py
from __future__ import annotations
import sys
from pathlib import Path
from dworshak_prompt import (InterruptBehavior, PromptMode, setup_dworshak_managers)
import logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stderr)
logger.addHandler(handler)
#logger.propagate = False  # Stop messages from going to the root logger
#logger.setLevel(logging.DEBUG)

DEFAULT_DWORSHAK_DIR = Path.home() / ".pipeline-eds"
dworshak_managers = setup_dworshak_managers(dir=DEFAULT_DWORSHAK_DIR)
dworshak_root_dir = dworshak_managers["root"] 
secret_mngr = dworshak_managers["secret"]
config_mngr = dworshak_managers["config"]
env_mngr = dworshak_managers["env"]
obtain_mngr = dworshak_managers["obtain"]

logger.debug(f"{env_mngr.path=}")
logger.debug(f"{config_mngr.path=}")
logger.debug(f"{secret_mngr.db_path=}")
# --- Control behavior of the Obtain class instance, beyong the default. 
# Impact the attibutes which are instatiated differently by default, to your desired behavior

obtain_mngr.interrupt_behavior = InterruptBehavior.EXIT
obtain_mngr.interface_priority = [PromptMode.WEB,PromptMode.GUI,PromptMode.CONSOLE]
obtain_mngr.interface_avoid = {}

'''# Alternative example 
# Add extra control features, compared to the standard obtain manager, but leverage the assigned pathing.
obtain_mngr = Obtain(
    config_path=config_mngr.path, 
    secret_path=secret_mngr.db_path, 
    interrupt_behavior=InterruptBehavior.EXIT,
    interface_priority=[PromptMode.WEB,PromptMode.GUI,PromptMode.CONSOLE]
    )
'''
