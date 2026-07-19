# src/pipeline_eds/server/trend_server_eds.py

from __future__ import annotations # Delays annotation evaluation
import msgspec.json # New import for fast JSON serialization
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import HTMLResponse, Response, JSONResponse, StreamingResponse # Using Response for msgspec
from starlette.exceptions import HTTPException
from starlette.requests import Request 
from msgspec import Struct 

from typer import BadParameter
from importlib import resources
from typing import Dict, Any, List, Optional
import requests
import logging

logger = logging.getLogger(__name__)

from pipeline_eds.helpers import PlotType, iso_time
from pipeline_eds.server.web_utils import launch_server_for_web_gui
from pipeline_eds.api.eds import core as eds_core
from pipeline_eds.interface.utils import save_history, load_history
from pipeline_eds.security_and_config import CredentialsNotFoundError
from pipeline_eds.xlsx_export import export_xlsx_for_results, save_xlsx_worbook_to_filestream

# Initialize Starlette app
app = Starlette(debug=True)

# --- Msgspec Struct for Request Body ---
class TrendRequest(Struct, tag=True):
    idcs: List[str]
    default_idcs: bool = False
    days: Optional[float] = None
    starttime: Optional[str] = None
    endtime: Optional[str] = None
    seconds_between_points: Optional[int] = None
    datapoint_count: Optional[int] = None
    force_webplot: bool = True
    force_matplotlib: bool = False
    plot_type: PlotType = PlotType.WEB
    use_mock: bool = False

# --- 1. Endpoint to Serve the HTML GUI ---

async def serve_gui(request: Request):
    """
    Handles GET /.
    Serves the eds_trend.html file by loading it as a package resource.
    """
    try:
        # Load the content of eds_trend.html as a resource
        index_content = resources.read_text('pipeline_eds.interface.web_gui.templates', 'eds_trend.html')        
        return HTMLResponse(index_content)
    
    except FileNotFoundError:
        return HTMLResponse(
            "<html><body><h1>Error 500: eds_trend.html resource not found.</h1>"
            "<h2>Check resource bundling configuration.</h2></body></html>", 
            status_code=500
        )
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>Resource Load Error: {e}</h1></body></html>", status_code=500)
    
    
# --- 2. API Endpoint for Core Logic ---

async def fetch_eds_trend(request: Request):
    """
    Handles POST /api/fetch_eds_trend.
    Fetches trend data and triggers plotting based on request parameters.
    """
    try:
        # 1. Decode the JSON request body using msgspec
        body = await request.body()
        request_data: TrendRequest = msgspec.json.decode(body, type=TrendRequest)
    
    except msgspec.DecodeError as e:
        # Catch JSON decoding errors (malformed JSON or invalid types)
        raise HTTPException(status_code=400, detail={"error": f"Invalid request body format or types: {e}"})
    except Exception as e:
        # Catch general body reading errors
        raise HTTPException(status_code=400, detail={"error": f"Failed to read request body: {e}"})

    # --- Core Logic Execution ---
    idcs_list = request_data.idcs
        
    try:
        # 1. Save history immediately if valid input was provided
        if idcs_list:
            # Reconstruct the space-separated string for history saving
            save_history(" ".join(idcs_list)) 
            
        data_buffer, _ = eds_core.fetch_trend_data(
            idcs=idcs_list, 
            starttime=request_data.starttime, 
            endtime=request_data.endtime, 
            days=request_data.days, 
            plant_name=None, 
            seconds_between_points=request_data.seconds_between_points, 
            datapoint_count=request_data.datapoint_count,
            default_idcs=request_data.default_idcs,
            use_mock=request_data.use_mock
        )
        
        # 2. Check for empty data
        if data_buffer.is_empty():
            response_data = {"no_data": True, "message": "No data returned."}
            return Response(
                content=msgspec.json.encode(response_data),
                media_type="application/json",
                status_code=200
            )
        
        # 3. Plotting
        eds_core.plot_trend_data(
            data_buffer, 
            request_data.force_webplot, 
            request_data.force_matplotlib,
            request_data.plot_type
        )
        
        response_data = {"success": True, "message": "Data fetched and plot initiated."}
        return Response(
            content=msgspec.json.encode(response_data),
            media_type="application/json",
            status_code=200
        )
    # ←←← REPLACE EVERYTHING FROM HERE DOWN TO THE END OF THE FUNCTION ←←←

    except requests.exceptions.ConnectTimeout:
        error_msg = "Connection to the EDS API timed out. Please check your VPN connection and try again."
        print(f"[EDS TREND SERVER] {error_msg}")
        response_data = {"error": error_msg}
        return Response(content=msgspec.json.encode(response_data), media_type="application/json", status_code=503)

    except BadParameter as e:
        error_msg = f"Input Error: {str(e).strip()}"
        response_data = {"error": error_msg}
        return Response(content=msgspec.json.encode(response_data), media_type="application/json", status_code=400)

    except CredentialsNotFoundError as e:
        error_msg = f"Configuration Required: {str(e)}"
        print(f"SECURITY ERROR: {e}")
        response_data = {"error": error_msg}
        return Response(content=msgspec.json.encode(response_data), media_type="application/json", status_code=400)

    except Exception as e:
        error_msg = f"Unexpected error fetching trend data: {str(e)}"
        print(f"[EDS TREND SERVER] {error_msg}")
        import traceback
        traceback.print_exc()
        response_data = {"error": error_msg}
        return Response(content=msgspec.json.encode(response_data), media_type="application/json", status_code=500)
        
async def download_xlsx(request: Request):
    """
    Handles POST /api/download_xlsx.
    Fetches raw trend data, formats it into a clean side-by-side Excel layout,
    and streams the resulting file directly to the user's browser.
    """
    try:
        body = await request.body()
        request_data: TrendRequest = msgspec.json.decode(body, type=TrendRequest)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": f"Invalid request body: {e}"})
    
    idcs_list = [s.upper() for s in request_data.idcs]
    
    try:
        from pipeline_eds.api.eds.rest.client import ClientEdsRest
        from pipeline_eds.api.eds.config import get_configurable_default_plant_name
        from pipeline_eds.api.eds.rest.config import get_eds_rest_api_credentials
        
        plant_name = get_configurable_default_plant_name()
        api_credentials = get_eds_rest_api_credentials(plant_name=plant_name)
        idcs_to_iess_suffix = api_credentials.get("idcs_to_iess_suffix")
        iess_list = [x + idcs_to_iess_suffix for x in idcs_list] 
        
        # Login n Fetch data 
        session = ClientEdsRest.login_to_session_with_api_credentials(api_credentials)
        from pipeline_eds.helpers import asses_time_range, nice_step
        
        dt_start, dt_finish = asses_time_range(starttime=request_data.starttime, endtime=request_data.endtime, days=request_data.days)
        
        if request_data.datapoint_count is not None:
            from pipeline_eds.time_manager import TimeManager
            step_seconds = int((TimeManager(dt_finish).as_unix() - TimeManager(dt_start).as_unix()) / request_data.datapoint_count)
        else:
            from pipeline_eds.time_manager import TimeManager
            step_seconds = nice_step(TimeManager(dt_finish).as_unix() - TimeManager(dt_start).as_unix())

        results = ClientEdsRest.load_historic_data(session, iess_list, dt_start, dt_finish, step_seconds)

        if not results:
            return Response(content=msgspec.json.encode({"error": "No data returned from API."}), media_type="application/json", status_code=404)
        
        file_path, workbook = export_xlsx_for_results(results, idcs_list, plant_name)
        filename = file_path.name
        logger.debug(f"{filename=}") 
        file_stream = save_xlsx_worbook_to_filestream(workbook)
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        return Response(content=msgspec.json.encode({"error": str(e)}), media_type="application/json", status_code=500) 
                   
# --- 3. API Endpoint for History ---

async def get_history(request: Request):
    """
    Handles GET /api/history.
    Returns the list of saved IDCS queries.
    """
    history = load_history()
    
    # Use msgspec for fast serialization
    content = msgspec.json.encode(history)
    
    return Response(
        content=content,
        media_type="application/json",
        status_code=200
    )


# --- Routing Definition (Replaces FastAPI decorators) ---

routes = [
    Route("/", endpoint=serve_gui, methods=["GET"]),
    Route("/api/fetch_eds_trend", endpoint=fetch_eds_trend, methods=["POST"]),
    Route("/api/download_xlsx", endpoint=download_xlsx, methods=["POST"]),
    Route("/api/history", endpoint=get_history, methods=["GET"]),
]

app.routes.extend(routes) # Add routes to the Starlette application

# --- Launch Command ---
def launch_server_for_web_interface_eds_trend():
    print("Launching EDS Trend HTML Interface...")
    
    # This single call checks the port, kicks off the pyhabitat background 
    # browser thread, pauses briefly for safety, and handles the blocking uvicorn process.
    launch_server_for_web_gui(app, host="127.0.0.1", port=8082)

if __name__ == "__main__":
    launch_server_for_web_interface_eds_trend()
