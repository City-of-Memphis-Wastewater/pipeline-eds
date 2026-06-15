# src/pipeline_eds/security.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import json
from pathlib import Path
import re
from typing import Dict

from .context import (obtain_mngr as obtain, secret_mngr)

# Define a standard configuration path for your package
CONFIG_PATH = Path.home() / ".pipeline-eds" / "config.json" ## configuration-example


class CredentialsNotFoundError(Exception):
    """
    Custom exception raised when required credentials or configuration values 
    cannot be found, are incomplete, or are cancelled by the user across 
    CLI, GUI, or Web prompts.
    
    This allows the CLI to gracefully handle configuration failures without 
    relying on web-specific exceptions like HTTPException.
    """
    def __init__(self, message="Configuration is missing, incomplete, or cancelled."):
        self.message = message
        super().__init__(self.message)


def json_heal(config_path = CONFIG_PATH):
    raw_text = config_path.read_text()
    # --- SELF-HEALING STEP: Clean the raw text ---
    # Remove all unneeded newlines that aren't inside the JSON structure
    # This turns your corrupt data back into a single valid JSON line
    cleaned_text = re.sub(r'[\r\n\t]+', ' ', raw_text)
    # Remove repeated spaces
    cleaned_text = re.sub(r' +', ' ', cleaned_text).strip()
    # 3. Attempt lax load with cleaned text
    try:
        config = json.loads(cleaned_text)
        print("Self-healing successful. File structure repaired.")
        
        # 4. Reformat and save the corrected file
        # This prevents the corruption from recurring on next load
        CONFIG_PATH.write_text(json.dumps(config, indent=4))
        print(f"File automatically reformatted to a clean structure at '{CONFIG_PATH.name}'.")
        return True
    except Exception:
        # Catch all errors during the healing attempt
        return False # Healing failed

def init_security():
    """Keyring is out, dworshak-access is in"""
    secret_mngr.initialize_vault()

def get_external_api_credentials(party_name: str, overwrite: bool = False) -> Dict[str, str]:
    """Retrieves API credentials for a given plant, prompting if necessary. 
    This is a standardized form. Alternative recommendation: Use piecemeal item by item closer to point of sale.
    This function demonstrates calling each element. You can reduce spaghetti and improve diverse specificity (without having to foresee keys like client or username) by not routing here.
    
    Interchangeble terms username and client_id are offered independantly and redundantly in the returned dictionary.
    This can be confusing for API clients that have both terms that mean different things (such as the MissionClient, though in that case the client=id is not sourced from stored credentials.) 
    The RJN API client was the first external API client, and it uses the term 'client_id' in place of the term 'username'.
    
    #mission_api_creds = get_external_api_credentials(party_name = party_name) # this function needs to be rewords to clarify which arguments are needed, so that a single configurable popup window can be served.
    THIS FUNCTION NEEDS TO BE REWORKED TO PASS IN EXPLICIT ARGUMENT KEYS WHICH ARE NEEDED FOR EACH CLIENT, SO THAT A SINGLE CONFIGURED POPUP WINDOW CAN BE SERVED 
    """
    service = f"pipeline-external-api-{party_name}"
    url = obtain.config(service = service, item = "url", message = f"Enter {party_name} API URL (e.g., http://api.example.com)", overwrite=overwrite).value
    username = obtain.secret( service = service, item = "username", message = f"Enter the username AKA client_id for the {party_name} API",hide=False, overwrite=overwrite).value
    password = obtain.secret(service = service, item = "password", message = f"Enter the password for the {party_name} API", overwrite=overwrite).value
    

    client_id = username # this only applies to RJN at last count
    
    #if not all([client_id, password]):
    #    raise CredentialsNotFoundError(f"API credentials for '{party_name}' not found. Please run the setup utility.")
        
    return {
        'url': url,
        'username': username,
        'client_id': client_id, # confusing for mission
        'password': password
    }



def _is_likely_ip(url: str) -> bool:
    """Simple heuristic to check if a string looks like an IP address."""
    parts = url.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not (0 <= int(part) <= 255):
            return False
    return True    

def prefix_http_url(url: str,
                    ) -> str:
    url.strip("http://")
    if url is None:
        return None
    if _is_likely_ip(url):
        url = f"http://{url}" # assume EDS patterns and port http if user just puts in an IP
    return url


# Example usage in your main pipeline
def frontload_build_all_credentials(forget : bool = False):
    """
    Sets up all possible API and database credentials for the pipeline_eds.
    
    This function is intended for "super users" who have cloned the repository.
    It will attempt to retrieve and, if necessary, prompt for all known
    credentials and configuration values in a single execution.
    
    This is an alternative to the just-in-time setup, which prompts for
    credentials only as they are needed.
    
    Note: This will prompt for credentials for all supported plants and external
    APIs in sequence.

    'forget' should be an option that can be toggled with env var PIPELINE_FORGET, which has a default of False when set up.
    Functions that require forget:
        - frontload_build_all_credentials()
        - SecurityAndConfig.get_config_with_prompt() # stored as plaintext
        - SecurityAndConfig.get_credential_with_prompt() # stored to dworshak
        
    """
    from pipeline_eds.api.eds.rest.config import get_eds_rest_api_credentials
    try:
        maxson_api_creds = get_eds_rest_api_credentials(plant_name = "Maxson")
        stiles_api_creds = get_eds_rest_api_credentials(plant_name = "Stiles")
        rjn_api_creds = get_external_api_credentials("RJN")
        
        # Now use the credentials normally in application logic, and they are now stored in plaintext and in encrypted vault db. 
        
    except CredentialsNotFoundError as e:
        print(f"Error: {e}")
        # Optionally, guide the user to the next step
        print("Tip: Run `your_package_name.configure()` or the corresponding CLI command.")

def not_enough_info():
    
    raise CredentialsNotFoundError(
        "Not enough configuration information provided to build credentials. "
        "The program requires user input or pre-configured values."
    )

if __name__ == "__main__":
    frontload_build_all_credentials()
    
