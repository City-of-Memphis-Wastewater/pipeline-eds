# src/pipeline_eds/gui_starlette_msgspec_plotly.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
import msgspec
import threading
import time
from threading import Lock
from pyhabitat import launch_browser_now  # Your WSL2 browser helper
import logging
from random import random

logger = logging.getLogger(__name__)

from pipeline_eds.boundary import Point, Series

# --- Shared plot buffer ---
plot_buffer = None  # Will be set by run()
buffer_lock = Lock()

# -----------------------------
# HTML template
# -----------------------------
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Live Plot</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
</head>

<body>
    <h2>Live EDS Data Plot</h2>

    <div id="live-plot" style="width:90%;height:80vh;"></div>

    <script>
        const layout = {
            margin: { t: 30 },
            legend: { orientation: "h" },
            xaxis: { title: "X" },
            yaxis: { title: "Y" }
        };

        let initialized = false;

        async function fetchData() {
            const response = await fetch("/data");
            return await response.json();
        }

        async function updatePlot() {
            const data = await fetchData();

            const traces = Object.entries(data).map(([label, series]) => ({
                x: series.x,
                y: series.y,
                name: label,
                mode: "lines+markers",
                type: "scatter"
            }));

            if (!initialized) {
                Plotly.newPlot("live-plot", traces, layout);
                initialized = true;
            } else {
                Plotly.react("live-plot", traces, layout);
            }
        }

        updatePlot();
        setInterval(updatePlot, 2000);
    </script>
</body>
</html>
"""

# -----------------------------
# Browser launcher
# -----------------------------
def open_browser(port):
    time.sleep(1)
    try:
        launch_browser_now(f"http://127.0.0.1:{port}")
    except Exception as e:
        logging.warning(f"Browser failed to launch: {e}")

# ----------------------------
# Route handlers
# ----------------------------

async def index(request):
    return HTMLResponse(HTML_TEMPLATE)

async def get_data(request):
    with buffer_lock:
        # If plot_buffer is a PlotBuffer instance:
        if hasattr(plot_buffer, 'snapshot'):
            data = plot_buffer.snapshot()
        # If plot_buffer is still our list[Series] fallback:
        elif isinstance(plot_buffer, list):
            data = {s.label: s.to_dict() for s in plot_buffer}
        else:
            data = {}
    return JSONResponse(data)

# -----------------------------
# Starlette app
# -----------------------------

routes = [
    Route("/", index),
    Route("/data", get_data),
]

app = Starlette(routes=routes)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# -----------------------------
# Interface runner
# -----------------------------
def run_plot(buffer: list[Series], port: int = 8000):
    global plot_buffer
    plot_buffer = buffer
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    logging.info("Starting Starlette + Uvicorn app...")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", reload=False)
    logging.info(f"Open your browser manually: http://127.0.0.1:{port}")

# -----------------------------
# Demo buffer
# -----------------------------
class DummyBuffer:
    def mock_data(self) -> set[Series]:
        points = [Point(x=i, y=random()) for i in range(10)]
        series1 = Series(label="Sensor A", points=points)
        series2 = Series(label="Sensor B", points=[Point(x=i, y=random()) for i in range(10)])

        buffer = [series1, series2]
        return buffer
    
if __name__ == "__main__":
    db = DummyBuffer()
    mock_data = db.mock_data()
    run_plot(mock_data)

