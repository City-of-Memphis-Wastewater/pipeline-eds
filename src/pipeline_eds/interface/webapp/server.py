# src/pipeline_eds/interface/webapp/server.py
"""
"""
import os
import sys
from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute, Route
from starlette.staticfiles import StaticFiles
from starlette.responses import JSONResponse, HTMLResponse
from starlette.templating import Jinja2Templates

# --- Application Configuration ---
# Determine the base directory for static and template files
#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#STATIC_DIR = Path(BASE_DIR) / "static"
#TEMPLATES_DIR = Path(BASE_DIR) /  "templates"

# --- Dynamic Path Resolution (PyInstaller & Local Dev) ---
# When bundled with PyInstaller, sys._MEIPASS points to the extracted _internal folder.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS) / "pipeline_eds" 
else:
    # Resolves up to src/pipeline_eds/ and navigates to data/webapp
    BASE_DIR = Path(__file__).resolve().parent.parent.parent 

WEBAPP_DIR = BASE_DIR / "data" / "webapp"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# --- Handlers ---
async def homepage(request):
    ## This will serve your main SvelteKit/Alpine.js index.html file
    #return HTMLResponse("<html><body><h1>Pipeline Dashboard</h1></body></html>")
    # Render main HTML template from data/webapp/templates/
    return templates.TemplateResponse(request, "eds_trend.html")

async def input_api(request):
    # This replaces one of your "pop-up" servers.
    # It handles input validation (using msgspec) and returns a result.
    return JSONResponse({"status": "ready", "fields": ["tag", "start_time"]})

async def plotting_ws(websocket):
    # This replaces your "plotting window" server.
    await websocket.accept()
    # Logic to stream plot data or status updates
    await websocket.send_json({"plot_status": "generating"})
    await websocket.close()

routes = [
    Route("/", endpoint=homepage),
    Route("/api/input", endpoint=input_api, methods=["GET", "POST"]),
    WebSocketRoute("/ws/plotting", endpoint=plotting_ws),
]

# Create the main Starlette app
app = Starlette(
    routes=routes,
    debug=True, # Set to False in production
)

# Mount static files (CSS, JS, images)
# The `include` section in your pyproject.toml already includes this directory.
# Mount static files (CSS, JS, images) from data/webapp/static/
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Expose the application factory function for Uvicorn
def get_app():
    return app