# pipeline/security.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import json
from pathlib import Path
import re
from typing import Dict, Set
import typer
import click.exceptions
import logging
import sys
import pyhabitat as ph
from pipeline_eds.state_manager import PromptManager # Import the manager class for type hinting
from enum import Enum, auto
import dworshak_access

# Define a standard configuration path for your package
CONFIG_PATH = Path.home() / ".pipeline-eds" / "config.json" ## configuration-example
CONFIG_FILE = Path.home() / ".pipeline-eds" / "secure_config.json"
KEY_FILE = Path.home() / ".pipeline-eds" / ".key"

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


class PromptMode(Enum):
    WEB = "web"
    GUI = "gui"
    CONSOLE = "console"
    NONE = "none"

class SecurityAndConfig:
    def __dict__(self):
        pass
    def __init__(self):
        pass
    
    @staticmethod
    def prompt_for_value(prompt_message: str=None,
                          hide_input: bool=False,
                          force: set[PromptMode] | None = None,
                          avoid: set[PromptMode] | None = None,
                          manager: PromptManager | None = None # <-- MANAGER IS ONLY FOR WEB GUI
                          ) -> str:
        """
        If force and avoid values are the same, avoid will win.

        Handles prompting with a fallback from CLI to GUI.
        ### **Platform Quirk: Input Cancellation ({Ctrl}+C)**
        Due to the underlying POSIX terminal handling on Linux and Termux,
        using {Ctrl}+C to cancel an input prompt will require the user
        to press {Enter} (or {Return}) immediately afterward to fully 
        submit the interrupt and abort the operation. 
        This behavior, the Enter key being necessary to finalize the interruption,
        is expected for POSIX systems, when using either the 
        `typer`/`click` framework, Python's built in input() function, or any alternative.
        This extra step is necessary due to the standard input terminal behavior
        in "cooked mode.".
        On  Windows, however, just {Ctrl}+C is expected to successfully perform a keyboard interrupt..
        """

        value = None # ensure safe defeault so that the except block handles properly, namely if the user cancels the typer.prompt() input with control+ c
        force = set(force or [])
        avoid = set(avoid or [])

        # avoid always wins
        force -= avoid
        
        # monkey patch known issue on wsl that is specific to this software()
        if ph.on_wsl():
            print("WSL monkeypatch, known tkinter inconsistency.")

            if PromptMode.GUI in force:
                force.discard(PromptMode.GUI)
                print("Force GUI removed under WSL")

            avoid.add(PromptMode.GUI)

        if (
            PromptMode.CONSOLE not in avoid
            and (
                PromptMode.CONSOLE in force
                or (ph.interactive_terminal_is_available() and not force)
            )
        ):
            try:
                # 1. CLI Mode (Interactive)
                typer.echo(f"\n --- Use CLI input --- ")
                if hide_input:
                    try:
                        from rich.prompt import Prompt
                        def secure_prompt(msg: str) -> str:
                            return Prompt.ask(msg, password=True)
                    except ImportError:
                        def secure_prompt(msg: str) -> str:
                            return typer.prompt(msg, hide_input=True)
                    value = secure_prompt(prompt_message)
                else:
                    value = typer.prompt(prompt_message, hide_input=False)

            except KeyboardInterrupt:
                typer.echo("\nInput cancelled by user.")
                return None
            return value
    
        # 2. GUI Branch
        if (
            PromptMode.GUI not in avoid
            and not ph.on_wsl()
            and (
                PromptMode.GUI in force
                or (ph.tkinter_is_available() and not force)
            )
        ):
            try:
                # 2. GUI Mode (Non-interactive fallback)
                from pipeline_eds.guiconfig import gui_get_input
                typer.echo(f"\n --- Non-interactive process detected. Opening GUI prompt. --- ")
                value = gui_get_input(prompt_message, hide_input)
                
                if value is not None:
                    return value
            except:
                # Fail-forward to Web if WSLg/X11 snaps
                print("Failing forwards to web prompt when gui prompt failed.")
                return SecurityAndConfig.prompt_for_value(
                    prompt_message, hide_input, avoid={PromptMode.GUI}, manager=manager
                )
        # 3. Web Branch
        if (
            PromptMode.WEB not in avoid
            and (
                PromptMode.WEB in force
                or (
            ph.web_browser_is_available() and force == ForcePrompt.NONE
        )):
            # 3. Browser Mode (Web Browser as a fallback)
            from pipeline_eds.config_via_web import browser_get_input

            # --- FIX: Retrieve the active manager if not provided ---
            if manager is None:
                try:
                    # We need to import the function that exposes the manager
                    #  The trend request is a particular page. We are trying to create a new kind of popup window (embedded in an existing page or in a dedicated page if none is available) 
                    # ; code for a generic config input field should not be overloy coupled to a specific dedicated interface for EDS trends
                    # However, that page can mention, if necesary, the dedicated injection point or "landing zone" for the config injection
                    from pipeline_eds.server.config_server import get_prompt_manager
                    
                    manager = get_prompt_manager()
                except ImportError:
                    # Handle case where server module isn't accessible (shouldn't happen here)
                    typer.echo("FATAL: Cannot retrieve PromptManager. Is server initialized?", err=True)
                    return None
                
            typer.echo(f"\n --- TKinter nor console is not available to handle the configuration prompt. Opening browser-based configuration prompt --- ")
            # We use the prompt message as the identifier key for the web service
            # because the true config_key is not available in this function's signature.
            value = browser_get_input(
                manager=manager,
                key=prompt_message, 
                prompt_message=prompt_message,
                hide_input=hide_input # <-- Passes input visibility to web config
            )

            if value is not None:
                return value

        # If all other options fail
        raise CredentialsNotFoundError(
            f"Configuration for '{prompt_message}' is missing or cancelled. "
            f"The program would cancel itself if neither an interactive terminal, nor a GUI display, nor a web browser is available. "
            f"Please use a configuration utility or provide the value programmatically."
        )

    def get_temporary_input(cls,prompt_message: str | None) -> str|None :
        """
        Seek a temporary user input value, not to be stored.
        Input options include console, pop-up window, or web browser input field, depending on what is available.
        """ 
        typer.echo(f"\n --- One-time temporary value required --- ")
        typer.echo("You may cancel the input to avoid entering a value.")

        try:
            new_value = SecurityAndConfig.prompt_for_value(
                prompt_message=prompt_message,
                hide_input=False
            )
        except (KeyboardInterrupt, EOFError):
            typer.echo("\n⚠️  Configuration prompt cancelled.")
            return None
        except Exception as e:
            typer.echo(f"\n⚠️  Unexpected error during prompt: {e}")
            return None
        if new_value is None:
            typer.echo("⚠️  No input provided. Returning None.")
            return None
        elif new_value == "":
            if ph.interactive_terminal_is_available() and not typer.confirm("⚠️  An empty string was provided. Are you sure about this?", default=True):
                return None
        # Normalize user input for empty-string passwords
        elif new_value in ("''", '""'):
            new_value = ""
        return new_value

    @staticmethod
    def get_config_with_prompt(config_key: str, 
                                prompt_message: str, 
                                overwrite: bool = False, 
                                forget: bool = False,
                                ) -> str | None:
        """
        Retrieves a config value from a local file, prompting the user and saving it if missing.
        
        Args:
            config_key: The key in the config file.
            prompt_message: The message to display if prompting is needed.
            overwrite: If True, the function will always prompt for a new value,
                    even if one already exists.
            forget: If True, credentials should not be stored to dworshak. 
                    and configs should not be stored to program-wide plaintext stored in AppData. 

        
        Returns:
            The configuration value (str) if successful, or None if the user cancels.
        
        """

        config = {}

        # --- Load existing config file safely ---
        if CONFIG_PATH.exists():
            try:
                # 1. Primary Load Attempt
                with open(CONFIG_PATH, "r") as f:
                    config = json.load(f)

            except json.JSONDecodeError as e:
                print(f"⚠️ Warning: Config file '{CONFIG_PATH.name}' is corrupted or improperly formatted. Attempting self-healing...")
                
                # 2. Attempt self-healing
                if json_heal(CONFIG_PATH):
                    try:
                        # 3. SECOND LOAD ATTEMPT: Must be in its own try block
                        with open(CONFIG_PATH, "r") as f:
                            config = json.load(f)
                    
                    except json.JSONDecodeError as repair_e:
                        # 4. Handle UNRECOVERABLE corruption after a failed heal attempt
                        typer.echo(f"⚠️ Warning: Existing config file '{CONFIG_PATH.name}' is corrupted. Self-healing failed. Error: {repair_e}")
                        if not typer.confirm("Do you want to reset the corrupted file to an empty file?", default=False):
                            typer.echo("-> Keeping existing corrupted file. Returning None for the requested value.")
                            return None
                        typer.echo("-> Resetting config file...")
                        config = {}
                else:
                    # 5. Handle failed self-healing (json_heal returned False)
                    typer.echo(f"⚠️ Warning: Existing config file '{CONFIG_PATH.name}' is corrupted. Self-healing failed.")
                    if not typer.confirm("Do you want to reset the corrupted file to an empty file?", default=False):
                        typer.echo("-> Keeping existing corrupted file. Returning None for the requested value.")
                        return None
                    typer.echo("-> Resetting config file...")
                    config = {}
                    
            except Exception as e:
                # Catch non-JSONDecode errors (e.g., File permission errors)
                typer.echo(f"⚠️  Failed to read config file: {e}")
                return None
            
        # Get the value from the config file, which will be None if not found
        value = config.get(config_key)
        
        # --- Handle existing value and overwrite logic ---
        # Check if a value exists and if the user wants to be sure about overwriting
        if value is not None and overwrite:
            typer.echo(f"\nValue for '{prompt_message}' is already set:")
            typer.echo(f"  '{value}'")
            if not typer.confirm("Do you want to overwrite it?", default=False):
                typer.echo("-> Keeping existing value.")
                return value

        # --- Prompt for new value if needed ---
        # If the value is None (not found), or if a confirmation to overwrite was given,
        # prompt for a new value
        if value is None or overwrite:
            typer.echo(f"\n --- One-time configuration required --- ")
            typer.echo("You may cancel the input to avoid entering a value.")

            try:
                new_value = SecurityAndConfig.prompt_for_value(
                    prompt_message=prompt_message,
                    hide_input=False
                )
            except (KeyboardInterrupt, EOFError):
                typer.echo("\n⚠️  Configuration prompt cancelled.")
                return None
            except Exception as e:
                typer.echo(f"\n⚠️  Unexpected error during prompt: {e}")
                return None
            if new_value is None:
                typer.echo("⚠️  No input provided. Configuration not saved.")
                return None
            # Normalize user input for empty-string passwords
            elif new_value in ("''", '""'):
                new_value = ""
            elif new_value == "":
                if ph.interactive_terminal_is_available() and not typer.confirm("⚠️  An empty string was provided. Are you sure about this?", default=True):
                    return None
            
            # --- Save updated configuration safely ---
            # Save the new value back to the file
            if forget:
                return new_value
            try:
                CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                config[config_key] = new_value
                with open(CONFIG_PATH, "w") as f:
                    json.dump(config, f, indent=4)
                typer.echo("Configuration stored.")
            except Exception as e:
                typer.echo(f"⚠️  Failed to save configuration: {e}")
                return None
            return new_value
        
        # --- Return existing value if no overwrite requested ---
        return value

    @staticmethod
    def get_credential_with_prompt(service_name: str, 
                                    item_name: str, 
                                    prompt_message: str, 
                                    hide: bool = False, 
                                    overwrite: bool = False,
                                    forget: bool = False,
                                    ) -> str | None:
        """
        Retrieves a secret from dworshak, prompting the user and saving it if missing.
        
        Args:
            service_name: The credential service name.
            item_name: The credential key.
            prompt_message: The message to display if prompting is needed.
            hide: True if the input should be hidden (getpass), False otherwise (input).
            overwrite: If True, the function will always prompt for a new credential,
                    even if one already exists.
            forget: If True, credentials should not be stored to dworshak, 
                    and configs should not be stored to program-wide plaintext stored in AppData. 

        Examples:
            OVERWRITE = False
            HIDEPASSWORD = False 

            service_name: service_name = f"pipeline-eds-db-{plant_name}"
            item_name: item_name = "username"
            prompt_message: prompt_message = f"Enter the IP address for your SOAP API (e.g., XXX.XX.X.XXX)" # no colon necessary, managed internally.
            hide_input: hide_input = HIDEPASSWORD 
            overwrite: overwrite = OVERWRITE

        Returns:
            The configuration value (str) if successful, or None if the user cancels.
        
        """
        
        #credential = keyring.get_password(service_name, item_name)
        credential = dworshak_access.get_secret(service_name, item_name)
        
        # Check if a credential exists and if the user wants to be sure about overwriting
        if credential is not None and overwrite:
            typer.echo(f"\nCredential for '{prompt_message}' already exists:")
            if hide:
                typer.echo(f"  '***'")
            else:
                typer.echo(f"  '{credential}'")
            
            if not typer.confirm("Do you want to overwrite it?", default=False):
                typer.echo("-> Keeping existing credential.")
                return credential

        # If the credential is None (not found), or if a confirmation to overwrite was given,
        # prompt for a new value.
        if credential is None or overwrite: 
            # -- Assign value of new_credential --
            try:
                print("Trying to prompt for credential ...")
                new_credential = SecurityAndConfig.prompt_for_value(
                    prompt_message=prompt_message, 
                    hide_input=hide
                )
                print("Success: prompted for credential.")
                print(f"new_credential = {new_credential}")
            except (KeyboardInterrupt, EOFError):
                typer.echo("\n⚠️  Credential prompt cancelled.")
                return None
            except Exception as e:
                typer.echo(f"\n⚠️  Unexpected error during credential prompt: {e}")
                return None

            if new_credential is None:
                typer.echo("⚠️  No input provided. Credential not saved.")
                return None
            elif new_credential == "":
                if ph.interactive_terminal_is_available() and not typer.confirm("⚠️  An empty string was provided. Are you sure about this?", default=True):
                    return None
            # Normalize user input for empty-string passwords
            if new_credential in ("''", '""'):
                new_credential = ""
            credential = new_credential
            

            if forget:
                return credential
                
            if not forget:
                # Store the new credential to dworshak
                try:
                    #keyring.set_password(service_name, item_name, new_credential)
                    dworshak_access.store_secret(service=service_name, item=item_name, secret=new_credential)
                except Exception as e:
                    typer.echo(f"⚠️  Failed to store credential: {e}")
                    return None

            typer.echo("✅  Credential stored securely.")

        # Return existing credential if no overwrite
        return credential

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

def ensure_dworshak():
    dworshak_access.initialize_vault()

def init_security():
    """Keyring is out, dworshak-access is in"""
    dworshak_access.initialize_vault()

def get_eds_local_db_credentials(plant_name: str, overwrite: bool = False) -> Dict[str, str]: # generalized for stiles and maxson
    """Retrieves all credentials and config for Stiles EDS Fallback DB, prompting if necessary."""
    service_name = f"pipeline-eds-db-{plant_name}"

    # 1. Get non-secret configuration from the local file
    port = SecurityAndConfig.get_config_with_prompt(config_key = "eds_db_port", prompt_message = "Enter EDS DB Port (e.g., 3306)")
    storage_path = SecurityAndConfig.get_config_with_prompt(config_key = "eds_db_storage_path", prompt_message = "Enter EDS database SQL storage path on your system (e.g., 'E:/SQLData/stiles')")
    database = SecurityAndConfig.get_config_with_prompt(config_key = "eds_db_database", prompt_message = "Enter EDS database name on your system (e.g., stiles)")

    # 2. Get secrets from dworshak
    username = SecurityAndConfig.get_credential_with_prompt(service_name = service_name, item_name = "username", prompt_message = "Enter your EDS system username (e.g. root)", hide=False, overwrite=overwrite)
    password = SecurityAndConfig.get_credential_with_prompt(service_name = service_name, item_name = "password", prompt_message = "Enter your EDS system password (e.g. Ovation1)", hide=True, overwrite=overwrite)
    

    return {
        'username': username,
        'password': password,
        'host': "localhost",
        'port': port,
        'database': database, # This could also be a config value if it changes
        'storage_path' : storage_path

    }




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
    service_name = f"pipeline-external-api-{party_name}"
    url = SecurityAndConfig.get_config_with_prompt(config_key = service_name, prompt_message = f"Enter {party_name} API URL (e.g., http://api.example.com)", overwrite=overwrite)
    username = SecurityAndConfig.get_credential_with_prompt( service_name = service_name, item_name = "username", prompt_message = f"Enter the username AKA client_id for the {party_name} API",hide=False, overwrite=overwrite)
    #client_id = SecurityAndConfig.get_credential_with_prompt(service_name = service_name, item_name = "client_id", prompt_message = f"Enter the client_id for the {party_name} API",hide=False, overwrite=overwrite)
    password = SecurityAndConfig.get_credential_with_prompt(service_name = service_name, item_name = "password", prompt_message = f"Enter the password for the {party_name} API", overwrite=overwrite)
    client_id = username # this only applies to RJN at last count
    
    #if not all([client_id, password]):
    #    raise CredentialsNotFoundError(f"API credentials for '{party_name}' not found. Please run the setup utility.")
        
    return {
        'url': url,
        'username': username,
        'client_id': client_id, # confusing for mission
        'password': password
    }


def get_all_configured_urls(only_eds: bool) -> Set[str]:
    """
    Reads the config file and returns a set of all URLs found.
    If only_eds is True, it returns only the EDS-related URLs.
    """
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

    urls = set()
    for key, value in config.items():
        if isinstance(value, str):
            # A simple check to see if the string looks like a URL
            if value.startswith(("http://", "https://")):
                if only_eds and "eds" in key.lower():
                    urls.add(value)
                elif not only_eds:
                    urls.add(value)
    return urls


def _is_likely_ip(url: str) -> bool:
    """Simple heuristic to check if a string looks like an IP address."""
    parts = url.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not (0 <= int(part) <= 255):
            return False
    return True    

def get_base_url_config_with_prompt(service_name: str, 
                                    prompt_message: str, 
                                    overwrite: bool = False
                                    ) -> str:
    #url = SecurityAndConfig.get_config_with_prompt(config_key = service_name, prompt_message = prompt_message, overwrite=overwrite)
    url = SecurityAndConfig.get_credential_with_prompt(service_name=service_name, item_name="base_url",prompt_message=prompt_message, overwrite=overwrite)
    if url is None:
        return None
    if _is_likely_ip(url):
        url = f"http://{url}" # assume EDS patterns and port http if user just puts in an IP
    return url

class CredentialsNotFoundError(Exception):
    """Custom exception for missing credentials."""
    pass

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
        
    Functions that store things are antithetical to 'forget':
        - _get_eds_local_db_credentials() # helper functon
    """
    
    try:
        maxson_api_creds = get_eds_rest_api_credentials(plant_name = "Maxson")
        stiles_api_creds = get_eds_rest_api_credentials(plant_name = "Stiles")
        stiles_db_creds = get_eds_local_db_credentials(plant_name = "Stiles")
        rjn_api_creds = get_external_api_credentials("RJN")
        
        # Now use the credentials normally in your application logic
        # ... your code to connect to services ...
        
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
    
