from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import requests
import platform
import subprocess
import sys
import time
import logging
from urllib.parse import urlparse
from urllib3.exceptions import NewConnectionError


logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

def test_connection_to_internet():
    try:
        # call Cloudflare's CDN test site, because it is lite.
        response = requests.get("http://1.1.1.1", timeout = 5)
        print("You are connected to the internet.")
    except:
        print(f"It appears you are not connected to the internet.")
        sys.exit()

def call_ping(url):
    parsed = urlparse(url)
    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "1", parsed.hostname]
    return subprocess.call(command) == 0  # True if ping succeeds

if __name__ == "__main__":
    from pipeline_eds.helpers import function_view
    function_view()