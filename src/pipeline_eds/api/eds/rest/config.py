# src/pipeline_eds/api/eds/rest/config.py
from __future__ import annotations
from typing import Dict
from dworshak_config import DworshakConfig
from dworshak_prompt import Obtain, InterruptBehavior, PromptMode

#from pipeline_eds.security_and_config import SecurityAndConfig, get_base_url_config_with_prompt, not_enough_info
from pipeline_eds.security_and_config import not_enough_info

obtain = Obtain(
    interrupt_behavior=InterruptBehavior.EXIT,
    interface_priority=[PromptMode.WEB,PromptMode.GUI,PromptMode.CONSOLE]
    )

config_mngr = DworshakConfig()

def get_rest_api_url(base_url: str | None = None,
                        eds_rest_api_port: int | None = 43084, 
                        eds_rest_api_sub_path: str = 'api/v1', 
                        ) -> str | None:
    """
    This is the recipe for forming the URL with that 
    makes REST API data requests to the EDS server.
    """
    if base_url is None:
        return None
    if base_url and str(eds_rest_api_port) and eds_rest_api_sub_path:
        eds_rest_api_url = base_url + ":" + str(eds_rest_api_port) + "/" + eds_rest_api_sub_path

    return eds_rest_api_url

def get_eds_rest_api_credentials(plant_name: str, overwrite: bool = False, forget: bool = False) -> Dict[str, str]:
    """Retrieves API credentials for a given plant, prompting if necessary."""

    #from pipeline_eds.api.eds.rest.client import ClientEdsRest
    from pipeline_eds.api.eds import config as eds_config
    from pipeline_eds.api.eds import security as eds_security
    from pipeline_eds.api.eds.rest import config as eds_rest_config # this file

    overwrite = False

    eds_base_url = eds_config.get_eds_base_url(plant_name=plant_name, overwrite=overwrite)
    idcs_to_iess_suffix = eds_config.get_idcs_to_iess_suffix(plant_name=plant_name, overwrite=overwrite)
    zd = eds_config.get_zd(plant_name=plant_name, overwrite=overwrite)
    
    config_mngr.set(service = "eds",item = f"rest_api_port_{plant_name}", value = "43084", overwrite=False) # pass value to users machine, but allow them to edit it manually if it exists by leaving overwrite as False
    eds_rest_api_port = obtain.config(service = "eds",item = f"rest_api_port_{plant_name}", message = f"Enter {plant_name} EDS REST API port", overwrite=overwrite, suggestion = "43084").value
    
    config_mngr.set(service = "eds",item = f"rest_api_sub_path_{plant_name}", value = "api/v1", overwrite=False) # pass value to users machine, but allow them to edit it manually if it exists by leaving overwrite as False
    eds_rest_api_sub_path = obtain.config(service = "eds",item = f"rest_api_sub_path_{plant_name}", message = f"Enter {plant_name} EDS REST API sub path", overwrite=overwrite, suggestion = "api/v1").value
    eds_rest_api_sub_path = str(eds_rest_api_sub_path).rstrip("/").lstrip("/").replace(r"\\","/").lower()

    username = eds_security.get_username(plant_name=plant_name, overwrite=overwrite)
    password = eds_security.get_password(plant_name=plant_name, overwrite=overwrite)

    # EDS REST API Pattern: url = f"http://{url}:43084/api/v1" # assume EDS patterna and port http and append api/v1 if user just puts in an IP
    
    from pipeline_eds.api.eds.rest.config import get_rest_api_url
    eds_rest_api_url = get_rest_api_url(eds_base_url, 
                                        str(eds_rest_api_port),
                                        eds_rest_api_sub_path
                                        ) 
    
    if eds_rest_api_url is None:
        not_enough_info()

    return {
        'url': eds_rest_api_url,
        'username': username,
        'password': password,
        'zd': zd,
        'idcs_to_iess_suffix': idcs_to_iess_suffix

        # The URL and other non-secret config would come from a separate config file
        # or be prompted just-in-time as we discussed previously.
    }