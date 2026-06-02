# src/pipeline_eds/api/eds/soap/client.py
from __future__ import annotations 
import sys
import logging
import time
from suds.client import Client as SudsClient # uses suds-py3
from dworshak_prompt import Obtain, InterruptBehavior, PromptMode
from dworshak_config import DworshakConfig

import logging
# Silence suds transport/client logs specifically
logging.getLogger('suds.client').setLevel(logging.CRITICAL)
logging.getLogger('suds.transport').setLevel(logging.CRITICAL)

from pipeline_eds.api.eds.config import get_service_name, get_configurable_default_plant_name, get_configurable_idcs_list
from pipeline_eds.api.eds.soap.config import get_eds_soap_api_url
from pipeline_eds.api.eds.security import get_username, get_password
from pipeline_eds.context import (obtain_mngr as obtain, config_mngr)


class ClientEdsSoap:
    def __init__(self, plant_name: str|None=None):
        if plant_name is None:
            self.plant_name = get_configurable_default_plant_name()
        else:
            self.plant_name=plant_name    

        # derived values
        self.service = get_service_name(plant_name=self.plant_name)
        self.eds_soap_api_url = get_eds_soap_api_url(plant_name=self.plant_name) 
        self._soapclient = None
        self.authstring = None
        self.tabular_data = None  # Explicit stat


    # --- Context Management (Pattern 2) ---
    def __enter__(self):
        """Called upon entering the 'with' block."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called upon exiting the 'with' block (for cleanup)."""
        
        # Logout from SOAP (if login was performed)
        if self.authstring:
            print(f"[{self.plant_name}] Attempting SOAP logout...")
            try:
                # We need a SOAP client instance to perform the logout
                if self.soapclient is None:
                    # Initialize just to logout, if not done already
                    self.soapclient = SudsClient(self.soap_url)
                self.soapclient.service.logout(self.authstring)
                print(f"[{self.plant_name}] Logout successful.")
            except Exception as e:
                print(f"[{self.plant_name}] Error during SOAP logout: {e}")
                
        # Return False to propagate exceptions, or True to suppress them
        return False
    
    @property
    def soapclient(self):
        if getattr(self, "_soapclient", None) is None:
        #if self._soapclient is None:
            self._set_client()
        return self._soapclient

    def _set_client(self):
        self._soapclient = SudsClient(self.eds_soap_api_url)
    

    def login_to_session(self):
        if self.authstring:
            return
        
        print(f"[{self.plant_name}] Connecting → {self.eds_soap_api_url}", file=sys.stderr)
        self.authstring = self.soapclient.service.login(self.username, self.password)
        if not self.authstring:
            print(f"[{self.plant_name}] Login failed", file=sys.stderr)
        print(f"[{self.plant_name}] Authenticated", file=sys.stderr)
        
    def ensure_required_configurable_client_vars(self):    
        self.username = get_username(plant_name=self.plant_name)
        self.password = get_password(plant_name=self.plant_name)
        self.iess_suffix = obtain.config(
            service = self.service, item = f"api_iess_suffix", message = f"IESS suffix for {self.plant_name}", suggestion = ".UNIT0@NET0"
        ).value
    
    def update_tabular_data(self, **kwargs) -> object | None:
        """
        [COMMAND]: Fetches data and updates self.tabular_data internally.
        This provides a single, reliable point of truth for state updates.
        """
        # 1. Perform the Query logic
        data = self._fetch_tabular_data_from_api(**kwargs)
        
        # 2. Perform the Assignment (The 'Double-Tap' handled inside)
        self.tabular_data = data
        
        # 3. Return the value for immediate use
        return self.tabular_data

    def _fetch_tabular_data_from_api(self, **kwargs) -> object | None:
        """
        [QUERY]: Pure calculation/fetch logic. 
        Does not touch 'self' attributes.
        """
        # massive logic block for soap_api_iess_request_tabular goes here.
        # ... implementation
        return self.soap_api_iess_request_tabular(**kwargs)

    def soap_api_iess_request_tabular(
        self,
        idcs: list[str] | None = None,
        *,
        start_time: int | None = None,
        end_time: int | None = None,
        step_seconds: int = 60,
        function: str = "AVG",
        shade_priority: int = 0,
    ) -> "object | None":
        """
        Core reusable method: fetch tabular (historical) data by IDCS → IESS.

        Returns TabularReply object on success, None on failure.
        """
        tabular_data = None

        # ———————————————————————— Config & Credentials ————————————————————————

        if idcs is None:
            idcs = get_configurable_idcs_list(self.plant_name)

        self.ensure_required_configurable_client_vars()
        
        # ———————————————————————— SOAP Session ————————————————————————
        try:
            self.login_to_session()
            if not self.authstring:
                return None

            # ———————————————————————— Resolve IESS names ————————————————————————
            idcs = [s.upper() for s in idcs]
            iess_list = [f"{idc}{self.iess_suffix}" for idc in idcs]

            # Verify points exist (optional but smart)
            filter_obj = self.soapclient.factory.create('PointFilter')
            existing_iess = []
            for iess in iess_list:
                filter_obj.iessRe = iess
                reply = self.soapclient.service.getPoints(self.authstring, filter_obj, None, None, None)
                if reply.matchCount == 1:
                    existing_iess.append(iess)
                else:
                    print(f"[{self.plant_name}] Point not found: {iess}")

            if not existing_iess:
                print(f"[{self.plant_name}] No valid points found")
                return None

            # ———————————————————————— Build & Submit Tabular Request ————————————————————————
            start = start_time or (int(time.time()) - 600)
            end = end_time or int(time.time())

            request = self.soapclient.factory.create('TabularRequest')
            period = self.soapclient.factory.create('TimePeriod')
            getattr(period, 'from').second = start
            period.till.second = end
            request.period = period
            request.step = self.soapclient.factory.create('TimeDuration')
            request.step.seconds = step_seconds

            for iess in existing_iess:
                item = self.soapclient.factory.create('TabularRequestItem')
                item.pointId = self.soapclient.factory.create('PointId')
                item.pointId.iess = iess
                item.shadePriority = shade_priority
                item.function = function
                request.items.append(item)

            request_id = self.soapclient.service.requestTabular(self.authstring, request)
            print(f"[{self.plant_name}] Tabular request submitted → {request_id}")

            # ———————————————————————— Poll until ready ————————————————————————
            while True:
                time.sleep(1)
                status_resp = self.soapclient.service.getRequestStatus(self.authstring, request_id)
                status = status_resp.status
                if status == 'REQUEST-SUCCESS':
                    tabular_data = self.soapclient.service.getTabular(self.authstring, request_id)
                    print(f"[{self.plant_name}] Trend data ready → {len(tabular_data.rows)} rows")
                    break
                elif status == 'REQUEST-FAILURE':
                    print(f"[{self.plant_name}] Request failed: {status_resp.message}")
                    break

        except Exception:
            from pipeline_eds.api.eds.exceptions import EdsLoginException
            EdsLoginException.connection_error_message(url=self.eds_soap_api_url)

        finally:
            if self.authstring:
                try:
                    self.soapclient.service.logout(self.authstring)
                except:
                    pass

        return tabular_data

    def get_tabular_as_dict(self,tabular_data):
        """Convert SUDS tabular data to a list of dicts based on Stiles schema."""
        if not tabular_data or not hasattr(tabular_data, 'rows'):
            return []

        # Extract point names from the metadata (e.g., 'I-0300A')
        point_names = [p.iess.split('.')[0] for p in tabular_data.pointsIds]

        clean_rows = []
        for row in tabular_data.rows:
            # Based on your trace: row['ts']['second']
            row_dict = {"timestamp": row.ts.second}
            
            for i, val_wrapper in enumerate(row.values):
                # iess usually looks like 'I-0300A.UNIT1@NET1'
                name = point_names[i]
                
                # Based on your trace: row['values'][0]['value']['dav']
                # We check if 'value' exists to avoid crashes on nulls
                if hasattr(val_wrapper, 'value'):
                    row_dict[name] = val_wrapper.value.dav
                    row_dict[f"{name}_quality"] = val_wrapper.quality
                else:
                    row_dict[name] = None
                    
            clean_rows.append(row_dict)

        return clean_rows
    
    def soap_api_iess_request_single_demo(self, idcs:list[str]|None):
        POINT_SID = 5395
        POINT_IESS = 'I-0300A.UNIT1@NET1'

        # --- Get encrypted credentials and plaintext configuration values --- 
        self.ensure_required_configurable_client_vars()

        try:
            # 1. Create the SOAP client
            print(f"Attempting to connect to WSDL at: {self.eds_soap_api_url}")
            soapclient = SudsClient(self.eds_soap_api_url)
            print("SOAP client created successfully.")
            # You can uncomment the line below to see all available services
            # print(soapclient)

            self.login_to_session()
            if not self.authstring:
                return

            # 3. Use the authstring to make other API calls
            
            # Example 1: ping (to keep authstring valid)
            print("\n--- Example 1: Pinging server ---")
            self.soapclient.service.ping(self.authstring)
            print("Ping successful.")

            # Example 2: getServerTime
            print("\n--- Example 2: Requesting server time ---")
            server_time_response = self.soapclient.service.getServerTime(self.authstring)
            print("Received server time response:")
            print(server_time_response)

            # Example 3: getServerStatus
            print("\n--- Example 3: Requesting server status ---")
            server_status_response = self.soapclient.service.getServerStatus(self.authstring)
            print("Received server status response:")
            print(server_status_response)
            
            # --- EXAMPLES OF  CSV DATA ---

            # Example 4: Get a specific point by IESS name
            ## WWTF,I-0300A,I-0300A.UNIT1@NET1,87,WELL,47EE48FD-904F-4EDA-9ED9-C622D1944194,eefe228a-39a2-4742-a9e3-c07314544ada,229,Wet Well
            print("\n--- Example 4: Requesting point by IESS name ")
            try:
                # Create a PointFilter object
                point_filter_iess = self.soapclient.factory.create('PointFilter')
                
                # Set the iessRe (IESS regular expression) filter
                # We use the exact name, but it also accepts wildcards
                #point_filter_iess.iessRe = POINT_IESS
                
                # Call getPoints(authstring, filter, order, startIdx, maxCount)
                # We set order, startIdx, and maxCount to None
                points_response_iess = self.soapclient.service.getPoints(self.authstring, point_filter_iess, None, None, None)
                print("Received getPoints response (by IESS):")
                print(points_response_iess)

            except Exception as e:
                print(f"Error during getPoints (by IESS): {e}")

            # Example 5: Get a specific point by SID
            # We will use '5395' (for I-5005A.UNIT1@NET1) from your CSV
            print("\n--- Example 5: Requesting point by SID ---")
            try:
                # Create another PointFilter object
                point_filter_sid = self.soapclient.factory.create('PointFilter')
                
                # Add the SID to the 'sid' array in the filter
                # (PointFilter definition on page 19 shows sid[] = <empty>)
                point_filter_sid.sid.append(POINT_SID)
                
                # Call getPoints
                points_response_sid = self.soapclient.service.getPoints(self.authstring, point_filter_sid, None, None, None)
                print("Received getPoints response (by SID):")
                print(points_response_sid)

            except Exception as e:
                print(f"Error during getPoints (by SID): {e}")

            # -----------------------------------------------

        except Exception:
            from pipeline_eds.api.eds.exceptions import EdsLoginException
            EdsLoginException.connection_error_message(url = self.eds_soap_api_url)
            
        finally:
            # 4. Logout using the authstring
            if self.authstring:
                try:
                    self.soapclient.service.logout(self.authstring)
                    print("Logout successful.")
                except Exception as e:
                    print(f"Error during logout: {e}")
            else:
                print("\nSkipping logout (was not logged in).")    
    
    
