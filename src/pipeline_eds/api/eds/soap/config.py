# src/pipeline_eds/api/eds/soap/config.py
from __future__ import annotations
from typing import Dict
from dworshak_prompt import Obtain, InterruptBehavior, PromptMode
import logging

logger=logging.getLogger(__name__)

from pipeline_eds.security_and_config import SecurityAndConfig, get_base_url_config_with_prompt, not_enough_info
from pipeline_eds.variable_clarity import Redundancy
from pipeline_eds.api.eds.config import get_service_name

obtain = Obtain(
    interrupt_behavior=InterruptBehavior.EXIT,
    interface_priority=[PromptMode.WEB,PromptMode.GUI,PromptMode.CONSOLE]
    )


def get_eds_soap_api_credentials(plant_name: str, overwrite: bool = False, forget: bool = False) -> Dict[str, str]:
    """Retrieves API credentials for a given plant, prompting if necessary."""
  

    service = get_service_name(plant_name = plant_name) # for secure credentials

    overwrite = False
    eds_base_url = get_base_url_config_with_prompt(service = service, prompt_message = f"Enter {plant_name} EDS base url (e.g., http://000.00.0.000, or just 000.00.0.000)")
    eds_soap_api_port = obtain.config(service = service, item = f"eds_soap_api_port", message = f"Enter {plant_name} EDS SOAP API port", overwrite=overwrite, suggestion = "43080").value
    eds_soap_api_sub_path = obtain.config(service = service, item = f"eds_soap_api_sub_path", message = f"Enter {plant_name} EDS SOAP API WSDL path", overwrite=overwrite, suggestion = "eds.wsdl").value
    username = obtain.secret(service = service, item = "username", message = f"Enter your EDS API username for {plant_name}", hide=False, overwrite=overwrite, suggestion = "admin").value
    password = obtain.secret(service = service, item = "password", message = f"Enter your EDS API password for {plant_name} (e.g. '')", overwrite=overwrite).value
    idcs_to_iess_suffix = obtain.config(service = service,item = f"api_iess_suffix", message = f"Enter iess suffix for {plant_name} (e.g., .UNIT0@NET0)", overwrite=overwrite, suggestion = "").value
    zd = obtain.config(service = service, item = f"eds_api_zd", message = f"Enter {plant_name} ZD (e.g., 'Maxson' or 'WWTF')", overwrite=overwrite, suggestion = "Maxson").value
    
    #if not all([username, password]):
    #    raise CredentialsNotFoundError(f"API credentials for '{plant_name}' not found. Please run the setup utility.")
    eds_soap_api_port = int(eds_soap_api_port)
    eds_soap_api_sub_path = eds_soap_api_sub_path

    # Comparable SOAP API function, for documentation:
    logger.warning(f"eds_base_url = {eds_base_url}")
    eds_soap_api_url = get_eds_soap_api_url(base_url = eds_base_url,
                                        eds_soap_api_port = str(eds_soap_api_port),
                                        eds_soap_api_sub_path = eds_soap_api_sub_path)
    if eds_soap_api_url is None:
        not_enough_info()
    
    return {
        'url': eds_soap_api_url,
        'username': username,
        'password': password,
        'zd': zd,
        'idcs_to_iess_suffix': idcs_to_iess_suffix

        # The URL and other non-secret config would come from a separate config file
        # or be prompted just-in-time as we discussed previously.
    }
    
#@Redundancy.set_on_return_hint(recipient=None,attribute_name="eds_soap_api_url")
def get_eds_soap_api_url(base_url: str | None = None,
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
    if base_url is None:
        return None
    
    if base_url and str(eds_soap_api_port) and eds_soap_api_sub_path:
        soap_api_url = base_url + ":" + str(eds_soap_api_port) + "/" + eds_soap_api_sub_path
    else:
        logging.info("get_eds_soap_api_url() returns None due to incomplete information.")
        return None
     
    return soap_api_url
