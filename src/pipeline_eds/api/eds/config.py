from __future__ import annotations
import re
from typing import List
from enum import Enum


from pipeline_eds.context import obtain_mngr as obtain
from pipeline_eds.security_and_config import prefix_http_url

class APIProtocol(str, Enum):
    REST = "REST"
    SOAP = "SOAP"

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
    prompt_message = f"Enter {plant_name} EDS base url (e.g., http://000.00.0.000, or just 000.00.0.000)"
    url = obtain.secret(service=service, item="base_url",message=prompt_message, overwrite=overwrite).value
    eds_base_url = prefix_http_url(url)
    return eds_base_url


def get_configurable_default_plant_name(overwrite=False) -> str :
    '''Comma separated list of plant names to be used as the default if none is provided in other commands.'''
    plant_name = obtain.config(service="eds",item = f"default_plantname", message = f"Enter plant name(s) to be used as the default", overwrite=overwrite).value
    if plant_name is not None and ',' in plant_name:
        plant_names = plant_name.split(',')
        return plant_names
    else:
        return plant_name

def get_configurable_default_api_protocol(
    overwrite: bool = False
) -> APIProtocol:
    """
    API protocol used by EDS.
    Allowed values: REST or SOAP.
    """
    api_protocol = config_mngr.set(
        service = "eds",
        item = f"api_protocol",
        value = APIProtocol.REST.value,
        overwrite=False
    )
    api_protocol = obtain.config(
        service="eds",
        item="api_protocol",
        message="Enter API protocol (REST or SOAP)",
        overwrite=overwrite,
        suggestion=APIProtocol.REST.value,
    )

    try:
        return APIProtocol(api_protocol.upper())
    except ValueError:
        raise ValueError(
            f"Invalid API protocol '{api_protocol}'. "
            f"Must be one of: {[p.value for p in APIProtocol]}"
        )
        
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
