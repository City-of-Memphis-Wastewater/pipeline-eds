# src/pipeline_eds/api/eds/security.py
from __future__ import annotations

from pipeline_eds.api.eds.config import get_configurable_default_plant_name
from pipeline_eds.api.eds.config import get_service_name
from pipeline_eds.context import obtain_mngr as obtain



def get_username(plant_name: str|None = None, overwrite: bool = False) -> str | None:
    """
    Retrieves the EDS username for the given plant name from configuration.
    """
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    if plant_name is None:
        return None
    username = obtain.secret(service = get_service_name(plant_name), item = "username", message = f"Enter your EDS API username for {plant_name}", overwrite=overwrite, suggestion = "admin").value
    return username

def get_password(plant_name: str|None = None, overwrite: bool = False) -> str | None:
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    if plant_name is None:
        return None
    password = obtain.secret(service = get_service_name(plant_name), item = "password", message = f"Enter your EDS API password for {plant_name} (e.g. '')", overwrite=overwrite).value
    return password
