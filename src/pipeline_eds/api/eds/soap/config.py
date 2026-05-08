# src/pipeline_eds/api/eds/soap/config.py
from __future__ import annotations
from typing import Dict
import logging

logger=logging.getLogger(__name__)

from pipeline_eds.security_and_config import SecurityAndConfig, get_base_url_config_with_prompt, not_enough_info
from pipeline_eds.variable_clarity import Redundancy
from pipeline_eds.api.eds.config import get_service_name, get_configurable_default_plant_name, get_eds_base_url
from pipeline_eds.context import (obtain_mngr as obtain, config_mngr)


def get_eds_soap_api_credentials(plant_name: str, overwrite: bool = False, forget: bool = False) -> Dict[str, str]:
    """Retrieves API credentials for a given plant, prompting if necessary."""

    service = get_service_name(plant_name = plant_name) # for secure credentials
    eds_soap_api_url = get_eds_soap_api_url(plant_name=plant_name) 

    username = obtain.secret(service = service, item = "username", message = f"Enter your EDS API username for {plant_name}", hide=False, overwrite=overwrite, suggestion = "admin").value
    password = obtain.secret(service = service, item = "password", message = f"Enter your EDS API password for {plant_name} (e.g. '')", overwrite=overwrite).value
    idcs_to_iess_suffix = obtain.config(service = service,item = f"api_iess_suffix", message = f"Enter iess suffix for {plant_name} (e.g., .UNIT0@NET0)", overwrite=overwrite, suggestion = "").value
    zd = obtain.config(service = service, item = f"eds_api_zd", message = f"Enter {plant_name} ZD (e.g., 'Maxson' or 'WWTF')", overwrite=overwrite, suggestion = "Maxson").value
    
    return {
        'url': eds_soap_api_url,
        'username': username,
        'password': password,
        'zd': zd,
        'idcs_to_iess_suffix': idcs_to_iess_suffix

        # The URL and other non-secret config would come from a separate config file
        # or be prompted just-in-time as we discussed previously.
    }
    
def get_eds_soap_api_url(plant_name: str | None = None, 
                overwrite: bool = False, 
                ) -> str | None:
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    service = get_service_name(plant_name=plant_name)
    base_url = get_eds_base_url(plant_name=plant_name, overwrite=overwrite)
    
    config_mngr.set(service = service,item = f"soap_api_port", value = "43080", overwrite=False) # pass value to user's machine, but allow them to edit it manually if it exists by leaving overwrite as False
    eds_soap_api_port = config_mngr.get(service = service,item = f"soap_api_port") # get value from user's machine, espiecially if they have edited it manually. Pass this as the suggestion if overwrite is used for prompting.
    eds_soap_api_port = obtain.config(
        service = service,item=f"soap_api_port", message="EDS SOAP port", suggestion = str(eds_soap_api_port)
    ).value        

    config_mngr.set(service = service,item = f"soap_api_sub_path", value = "eds.wsdl", overwrite=False) # pass value to user's machine, but allow them to edit it manually if it exists by leaving overwrite as False
    eds_soap_api_sub_path = config_mngr.get(service = service,item = f"soap_api_sub_path") # get value from user's machine, espiecially if they have edited it manually. Pass this as the suggestion if overwrite is used for prompting.
    eds_soap_api_sub_path = obtain.config(
        service = service, item=f"soap_api_sub_path", message="WSDL path", suggestion = str(eds_soap_api_sub_path)
    ).value

    eds_soap_api_url = form_eds_soap_api_url(base_url, eds_soap_api_port, eds_soap_api_sub_path)
    if eds_soap_api_url is None:
        not_enough_info()

    return eds_soap_api_url

#@Redundancy.set_on_return_hint(recipient=None,attribute_name="eds_soap_api_url")
def form_eds_soap_api_url(base_url: str | None = None,
                eds_soap_api_port: int | None = 43080, 
                eds_soap_api_sub_path: str | None = 'eds.wsdl', 
                ) -> str | None:
    """
    This is the recipe for forming the URL that 
    makes SOAP API data requests to the EDS server.
    
    WSDL (Web Service Description Language) is an XML-based language used
      to describe the functionality of a SOAP-based web service. 
      It acts as a contract between the service provider and the consumer, 
      detailing the operations available, the input/output parameters, 
      and the communication protocols.

    source: https://www.soapui.org/docs/soap-and-wsdl/working-with-wsdls/

    """
    if base_url and str(eds_soap_api_port) and eds_soap_api_sub_path:
        eds_soap_api_url = base_url + ":" + str(eds_soap_api_port) + "/" + eds_soap_api_sub_path
    else:
        logging.info("get_eds_soap_api_url() returns None due to incomplete information.")
        return None

    return eds_soap_api_url


