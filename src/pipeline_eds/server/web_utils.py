# src/pipeline_eds/server/web_utils.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import time
import socket
import uvicorn # Used for launching the server
from pathlib import Path
from pyhabitat import launch_browser_after_http_poll 
import logging

logger = logging.getLogger(__name__)

def find_open_port(start_port: int = 8082, max_port: int = 8100) -> int:
    """
    Finds an available TCP port starting from `start_port` up to `max_port`.
    Returns the first available port.
    """
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                s.close()
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available port found between {start_port} and {max_port}.")

# --- 1. Serve Static Files ---


def launch_server_for_web_gui(app, host: str = "127.0.0.1", port: int = 8082):
    """Launches the server using uvicorn and kicks off a browser poll thread."""
    try:
        port = find_open_port(port, port + 50)
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
