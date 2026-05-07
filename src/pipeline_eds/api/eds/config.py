from __future__ import annotations
import re
from typing import List

from pipeline_eds.context import obtain_mngr as obtain
from pipeline_eds.security_and_config import get_base_url_config_with_prompt


def get_service_name(plant_name: str|None = None) -> str | None:
    """
    Describe the standardized string describing the service name that will be known to the configuration file.
    """
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    if plant_name is None:
        return None
    service = f"eds_{plant_name.upper()}" 
    return service

def get_eds_base_url(plant_name: str|None = None, overwrite: bool = False) -> str | None:
    """
    Retrieves the EDS base URL for the given plant name from configuration.
    """
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    if plant_name is None:
        return None
    service = get_service_name(plant_name=plant_name)
    eds_base_url = get_base_url_config_with_prompt(service = service, prompt_message = f"Enter {plant_name} EDS base url (e.g., http://000.00.0.000, or just 000.00.0.000)", overwrite=overwrite)
    return eds_base_url


def get_configurable_default_plant_name(overwrite=False) -> str :
    '''Comma separated list of plant names to be used as the default if none is provided in other commands.'''
    plant_name = obtain.config(service="eds",item = f"configurable_plantname_eds_api", message = f"Enter plant name(s) to be used as the default", overwrite=overwrite).value
    if plant_name is not None and ',' in plant_name:
        plant_names = plant_name.split(',')
        return plant_names
    else:
        return plant_name


def get_idcs_to_iess_suffix(plant_name: str|None = None, overwrite: bool = False) -> str | None:
    """
    Retrieves the iess suffix for the given plant name from configuration.
    Prompts the user if not found and overwrite is True.
    """
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    if plant_name is None:
        return None
    service = get_service_name(plant_name = plant_name)
    idcs_to_iess_suffix = obtain.config(service = service,item = f"api_iess_suffix", message = f"Enter iess suffix for {plant_name}", overwrite=overwrite, suggestion = ".UNIT0@NET0").value
    return idcs_to_iess_suffix

def get_zd(plant_name: str|None = None, overwrite: bool = False) -> str | None:
    """
    Retrieves the iess suffix for the given plant name from configuration.
    Prompts the user if not found and overwrite is True.
    """
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    if plant_name is None:
        return None
    service = get_service_name(plant_name=plant_name)
    zd = obtain.config(service = service,item = f"zd", message = f"Enter {plant_name} ZD (e.g., 'Maxson' or 'WWTF')", overwrite=overwrite, suggestion = "Maxson").value
    return zd

def get_configurable_idcs_list(plant_name: str, overwrite: bool = False) -> List[str]:
    """
    Retrieves a list of default IDCS points for a specific plant from configuration. 
    If not configured, it prompts the user to enter them and saves them.
    
    The function handles IDCS values separated by one or more spaces or commas.
    """
    
    message = (
        f"Enter default IDCS values for the {plant_name} plant"
    )
    service = get_service_name(plant_name=plant_name)
    
    idcs_value = obtain.config(service = service, item = f"default_idcs", message = message, overwrite=overwrite, suggestion = "m100fi fi8001 m310li").value
    
    if not idcs_value:
        return []
    
    # Use re.split to split by multiple delimiters: 
    # r'[,\s]+' means one or more commas (,) OR one or more whitespace characters (\s).
    raw_idcs_list = re.split(r'[,\s]+', idcs_value)
    
    # Filter out any empty strings resulting from the split (e.g., if input was "IDCS1,,IDCS2")
    # and strip leading/trailing whitespace from each element.
    idcs_list = [
        item.strip() 
        for item in raw_idcs_list 
        if item.strip()
    ]
    
    return idcs_list