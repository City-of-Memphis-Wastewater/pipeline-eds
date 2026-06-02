# src/pipeline_eds/api/eds/soap/demo.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import logging
import time


from pipeline_eds.decorators import log_function_call
from pipeline_eds.api.eds.soap.client import ClientEdsSoap

@log_function_call(level=logging.DEBUG)
def demo_eds_soap_api_tabular_classic():
    client_eds_soap = ClientEdsSoap(plant_name = "Stiles")
    client_eds_soap.soap_api_iess_request_tabular(idcs = ['I-0300A','I-0301A'])
    
if __name__ == "__main__":

    '''
    - auto id current function name. solution: decorator, @log_function_call
    - print only which vars succeed
    '''
    import sys
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else "default"

    logging.info("CLI started")

    if cmd == "demo_soap_tabular_classic": 
        demo_eds_soap_api_tabular_classic()
    else:
        print("Usage options: \n" 
        "uv run python -m pipeline_eds.api.eds.soap.demo demo_soap_tabular_classic"
        )
