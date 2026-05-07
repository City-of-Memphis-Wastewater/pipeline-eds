# src/pipeline_eds/api/eds/rest/config.py
from __future__ import annotations
from typing import Dict
import logging

from pipeline_eds.security_and_config import not_enough_info
from pipeline_eds.api.eds.config import get_service_name, get_configurable_default_plant_name, get_eds_base_url
from pipeline_eds.context import (obtain_mngr as obtain, config_mngr)

def get_eds_rest_api_credentials(plant_name: str, overwrite: bool = False, forget: bool = False) -> Dict[str, str]:
    """Retrieves API credentials for a given plant, prompting if necessary."""

    #from pipeline_eds.api.eds.rest.client import ClientEdsRest
    from pipeline_eds.api.eds import config as eds_config
    from pipeline_eds.api.eds import security as eds_security
    from pipeline_eds.api.eds.rest import config as eds_rest_config # this file

    overwrite = False

    from pipeline_eds.api.eds import config as eds_config
    
    idcs_to_iess_suffix = eds_config.get_idcs_to_iess_suffix(plant_name=plant_name, overwrite=overwrite)
    zd = eds_config.get_zd(plant_name=plant_name, overwrite=overwrite)
    
    username = eds_security.get_username(plant_name=plant_name, overwrite=overwrite)
    password = eds_security.get_password(plant_name=plant_name, overwrite=overwrite)

    eds_rest_api_url = get_eds_rest_api_url(plant_name=plant_name,overwrite=overwrite)
    

    return {
        'url': eds_rest_api_url,
        'username': username,
        'password': password,
        'zd': zd,
        'idcs_to_iess_suffix': idcs_to_iess_suffix

        # The URL and other non-secret config would come from a separate config file
        # or be prompted just-in-time as we discussed previously.
    }


def get_eds_rest_api_url(plant_name: str | None = None, 
                overwrite: bool = False, 
                ) -> str | None:
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    service = get_service_name(plant_name=plant_name)
    base_url = get_eds_base_url(plant_name=plant_name, overwrite=overwrite)
    
    config_mngr.set(service = service,item = f"rest_api_port", value = "43084", overwrite=False) # pass value to users machine, but allow them to edit it manually if it exists by leaving overwrite as False
    eds_rest_api_port = obtain.config(
        service = service,item=f"rest_api_port", message="EDS rest port", suggestion = "43084"
    ).value        

    config_mngr.set(service = service,item = f"rest_api_sub_path", value = "api/v1", overwrite=False) # pass value to users machine, but allow them to edit it manually if it exists by leaving overwrite as False
    eds_rest_api_sub_path = obtain.config(
        service = service, item=f"rest_api_sub_path", message="REST API sub path", suggestion = "ap1/v1"
    ).value
    eds_rest_api_sub_path = str(eds_rest_api_sub_path).rstrip("/").lstrip("/").replace(r"\\","/").lower()

    eds_rest_api_url = form_eds_rest_api_url(base_url, eds_rest_api_port, eds_rest_api_sub_path)
    if eds_rest_api_url is None:
        not_enough_info()

    return eds_rest_api_url

def form_eds_rest_api_url(base_url: str | None = None,
                eds_rest_api_port: int | None = 43084, 
                eds_rest_api_sub_path: str | None = 'api/v1', 
                ) -> str | None:
    """
    This is the recipe for forming the URL that 
    makes REST API data requests to the EDS server.
    # EDS REST API Pattern: url = f"http://{url}:43084/api/v1" # assume EDS patterna and port http and append api/v1 if user just puts in an IP
    
    """
    if base_url and str(eds_rest_api_port) and eds_rest_api_sub_path:
        eds_rest_api_url = base_url + ":" + str(eds_rest_api_port) + "/" + eds_rest_api_sub_path
    else:
        logging.info("get_eds_rest_api_url() returns None due to incomplete information.")
        return None

    return eds_rest_api_url