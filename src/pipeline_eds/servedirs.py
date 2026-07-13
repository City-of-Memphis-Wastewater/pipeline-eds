#!/usr/bin/env python3
"""
servedirs_flask.py - tiny directory server with Flask UI + shutdown button
"""

from __future__ import annotations

import os
import signal
from pathlib import Path
from urllib.parse import quote
from flask import Flask, abort, send_from_directory, render_template_string

# ----------------------------
# HTML template (Jinja2 syntax)
# ----------------------------

HTML_PAGE = """<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta charset="utf-8">
  <title>servedirs</title>
  <style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 900px;
      margin: 40px auto;
      background: #f6f7f9;
      color: #111;
    }
    h1 { font-size: 20px; }
    .bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    button {
      padding: 8px 12px;
      border: 0;
      border-radius: 6px;
      background: #d9534f;
      color: white;
      cursor: pointer;
    }
    button:hover {
      background: #c9302c;
    }
    ul {
      list-style: none;
      padding: 0;
      background: white;
      border-radius: 10px;
      padding: 10px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }
    li {
      padding: 6px 8px;
    }
    a {
      text-decoration: none;
      color: #0d6efd;
    }
  </style>
</head>
<body>
  <div class="bar">
    <h1>servedirs (Flask)</h1>
    <button onclick="fetch('/shutdown', {method: 'POST'})
      .then(() => document.body.innerHTML='<h2>Server stopped</h2>')">
      Stop server
    </button>
  </div>

  <ul>
    {% if show_parent %}
      <li><a href="{{ parent_url }}">../ (parent)</a></li>
    {% endif %}
    {% for item in items %}
      <li><a href="{{ item.link }}">{{ item.display }}</a></li>
    {% endfor %}
  </ul>
</body>
</html>
"""

# Initialize Flask app
app = Flask(__name__)
BASE_DIRECTORY = Path(os.getcwd()).resolve()


# ----------------------------
# Core Logic & Routing
# ----------------------------

@app.route('/', defaults={'req_path': ''}, methods=['GET'])
@app.route('/<path:req_path>', methods=['GET'])
def list_or_serve(req_path):
    # Security block: resolve paths fully to prevent directory traversal exploits
    target_path = (BASE_DIRECTORY / req_path).resolve()

    # Ensure target path sits underneath the declared root directory
    if not str(target_path).startswith(str(BASE_DIRECTORY)):
        return abort(403, "Access denied")

    if not target_path.exists():
        return abort(404, "File or folder not found")

    # If it is a file, stream it directly with correct MIME types
    if target_path.is_file():
        return send_from_directory(target_path.parent, target_path.name)

    # Otherwise, generate the directory index view
    try:
        entries = sorted(os.listdir(target_path))
    except OSError:
        return abort(403, "No permission to list directory")

    items = []
    show_parent = target_path != BASE_DIRECTORY
    
    # Safely compute parent directory path string relative to root
    parent_url = "/" + str(req_path.rsplit('/', 1)[0]) if '/' in req_path else "/"

    for name in entries:
        full_item_path = target_path / name
        is_dir = full_item_path.is_dir()

        # Build absolute UI URL paths for web anchors
        url_subpath = f"{req_path}/{name}".strip("/")
        link = f"/{quote(url_subpath)}" + ("/" if is_dir else "")
        
        # Format list string suffix
        display = name + ("/" if is_dir else "")

        items.append({
            "display": display,
            "link": link
        })

    # Jinja engine securely escapes variables automatically to mitigate XSS
    return render_template_string(
        HTML_PAGE,
        items=items,
        show_parent=show_parent,
        parent_url=parent_url
    )


@app.route('/shutdown', methods=['POST'])
def shutdown():
    print("[servedirs] Received remote shutdown request. Exiting...")
    
    # Flask runs inside a main execution loop thread. 
    # Sending a SIGINT signal cleanly unwinds the application server instance.
    os.kill(os.getpid(), signal.SIGINT)
    return "", 204


# ----------------------------
# Server runner
# ----------------------------

def serve_directory_custom(path: str | Path, host="127.0.0.1", port=8000):
    global BASE_DIRECTORY
    BASE_DIRECTORY = Path(path).resolve()

    if not BASE_DIRECTORY.exists():
        raise FileNotFoundError(BASE_DIRECTORY)

    print(f"Serving: {BASE_DIRECTORY}")
    print(f"URL: http://{host}:{port}/")
    print("Press Ctrl+C or use /shutdown")

    # threaded=True gives you equivalent behavior to ThreadingHTTPServer
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    serve_directory_custom(args.path, args.host, args.port)
