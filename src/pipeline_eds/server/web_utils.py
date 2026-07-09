# src/pipeline_eds/server/web_utils.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import time
import uvicorn # Used for launching the server
from pathlib import Path
from pyhabitat import launch_browser_after_http_poll, find_open_port 
import logging

logger = logging.getLogger(__name__)

def launch_server_for_web_gui(app, host: str = "127.0.0.1", port: int = 8082):
    """Launches the server using uvicorn and kicks off a browser poll thread."""
    try:
        port = find_open_port(port, host, port + 50)
    except RuntimeError as e:
        raise RuntimeError(f"Failed to start server: {e}")
    
    url = f"http://{host}:{port}"
    print(f"Starting Generalized Web Server at {url}")
    
    # 1. Fire and forget the pyhabitat daemon thread loader
    # This completely replaces your manual launch_browser_after_http_poll block
    launch_browser_after_http_poll(url, timeout=5.0, poll_interval=0.2)
    time.sleep(0.5)
    
    # 2. Start the server (Blocking call)
    uvicorn.run(app, host=host, port=port, log_level="info")
