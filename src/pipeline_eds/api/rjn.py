from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import requests
import logging
from typing import Union # for 3.8 friendly type suggestions

from pipeline_eds.decorators import log_function_call
from pipeline_eds.time_manager import TimeManager
from pipeline_eds.context import secret_mngr as secret_manager

logger = logging.getLogger(__name__)

class ClientRjn:
    def __init__(self, api_url):
        self.api_url = api_url.rstrip('/')
        self.session = None
    
    def login_to_session(self,client_id, password):
        logger.info("ClientRjn.login_to_session()")
        session = requests.Session()
        api_url = self.api_url

        data = {'client_id': client_id, 'password': password, 'type': 'script'}
        
        try:    
            response = session.post(f'{api_url}/auth', json=data, verify=True)

            # 1. Handle Authentication/HTTP failures specifically
            if response.status_code == 401:
                logging.error("Authentication Failed: Incorrect credentials provided to RJN Clarity.")
                return False
            
            response.raise_for_status() # catch 4xx/5xx html status

            # 2. Check for empty response
            if not response.text:
                logging.error(f"Empty response received from {self.api_url}/auth")
                return False
            # Safely attempt to parse JSON
            try:
                payload = response.json()
                token = payload.get('token')
                if not token:
                    logging.error("Login successful but no token found in response.")
                    return False
                
                session.headers['Authorization'] = f'Bearer {token}'
                print("Status code:", response.status_code)
                #print("Response text:", response.text)
                self.session = session
                return True
            
            except requests.exceptions.JSONDecodeError:
                logging.error(f"Expected JSON but got: {response.text[:100]}")
                return False
        
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}") # e.g. 401 Unauthorized
            return False
        
        except requests.exceptions.SSLError as ssl_err:
            logging.warning("SSL verification failed. Will retry on next scheduled cycle.")
            logging.debug(f"SSL error details: {ssl_err}")
            return False

        except requests.exceptions.ConnectionError as conn_err:
            logging.warning("Connection error during authentication. Will retry next hour.")
            logging.debug(f"Connection error details: {conn_err}")
            return False

        except Exception as general_err:
            logging.error("Unexpected error during login.", exc_info=True)
            return False


    def send_data_to_rjn(self, project_id:str, entity_id:int, timestamps: list[Union[int, float, str]], values: list[float]): # this would be beter as a dict with keys
        if timestamps is None:
            raise ValueError("timestamps cannot be None")
        if values is None:
            raise ValueError("values cannot be None")
        if not isinstance(timestamps, list):
            raise ValueError("timestamps must be a list. If you have a single timestamp, use: [timestamp] ")
        if not isinstance(values, list):
            raise ValueError("values must be a list. If you have a single value, use: [value] ")
        # Check for matching lengths of timestamps and values
        if len(timestamps) != len(values):
            raise ValueError(f"timestamps and values must have the same length: {len(timestamps)} vs {len(values)}")

        timestamps_str = [TimeManager(ts).as_formatted_date_time() for ts in timestamps]

        url = f"{self.api_url}/projects/{project_id}/entities/{entity_id}/data"
        params = {
            "interval": 300,    
            "import_mode": "OverwriteExistingData",
            "incoming_time": "DST"#, # DST seemed to fail and offset by an hour into the future. UTC with central time seemed to fail and offset the data 5 hours into the past. 
            #"local_timezone": "CST_CentralStandardTime"
        }
        body = {
        "comments": "Imported from EDS.",
        "data": dict(zip(timestamps_str, values))  # Works for single or multiple entries
        }
        

        response = None
        try:
            response = self.session.post(url=url, json= body, params = params)

            print("Status code:", response.status_code)
            #print("Response text:", response.text)
            if response is None:
                print("Response = None, job cancelled")
            else:
                response.raise_for_status()
                print(f"Sent timestamps and values to entity {entity_id} (HTTP {response.status_code})")
                return True
        except requests.exceptions.ConnectionError as e:
            print("Skipping ClientRjn.send_data_to_rjn() due to connection error")
            print(e)
            return False
        except requests.exceptions.RequestException as e:
            print(f"Error sending data to RJN: {e}")
            if response is not None:# and response.status_code != 500:
                logging.debug(f"Response content: {response.text}")  # Print error response
                
            return False

@log_function_call(level=logging.DEBUG)
def demo_rjn_ping():
    from pipeline_eds.calls import call_ping

    service = "pipeline-rjn-clarity"
    base_url = secret_manager.get(service = service, item = "url", fail = True)
    client_id = secret_manager.get(service = service, item = "username", fail = True)
    password = secret_manager.get(service = service, item = "password", fail = True)
    crjn = ClientRjn(url = base_url)
    crjn.login_to_session(client_id = client_id, password = password)
                                    
    if crjn.session is None:
        logger.warning("RJN session not established. Skipping RJN-related data transmission.\n")
        return
    else:
        logger.info("RJN session established successfully.")
        response = call_ping(base_url)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "default"

    if cmd == "ping":
        demo_rjn_ping()
    else:
        print("Usage options: \n"
        "uv run python -m pipeline_eds.api.rjn ping")