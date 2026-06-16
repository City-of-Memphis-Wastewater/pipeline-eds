#
from __future__ import annotations
import logging

logger=logging.getLogger(__name__)

DEFAULT_TIMEZONE = "America/Chicago"

def get_timezone_config():
    try:
        timezone_config = config_mngr.set(service = service,item = f"timezone", value = DEFAULT_TIMEZONE, overwrite=False)
        timezone_config = obtain_mngr.config(service = service, item = "timezone", suggestion=timezone_config).value
        if False:
            check_timezone_validity(timezone_config)
    except:
        timezone_config = DEFAULT_TIMEZONE
    return timezone_config
    
def check_timezone_validity(timezone=str|None):
    pass
