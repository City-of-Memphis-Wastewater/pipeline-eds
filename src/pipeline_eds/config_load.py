#
from __future__ import annotations
import logging

logger=logging.getLogger(__name__)

from pipeline_eds.helpers import load_toml

DEFAULT_TIMEZONE = "America/Chicago"

def get_timezone_config():
    config = load_toml(self.workspace_manager.get_configuration_file_path())
    try:
        timezone_config = config_mngr.set(service = service,item = f"timezone", value = DEFAULT_TIMEZONE, overwrite=False)
        timezone_config = obtain_mngr.config(service = service, item = "timezone", suggestion=timezone_config).value
        if False:
            check_timezone_validity(timezone_config)
    except:
        timezone_config = DEFAULT_TIMEZONE

def check_timezone_validity(timezone=str|None):
    pass
