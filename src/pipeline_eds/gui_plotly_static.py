# src/pipeline_eds_gui_plotly_static.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import plotly.graph_objs as go
import plotly.io as pio
import webbrowser
import tempfile
import threading
import pyhabitat
from pathlib import Path
import logging
from pyhabitat.launch import launch_file

from pipeline_eds.plottools import normalize, normalize_ticks, get_ticks_array_n
from pipeline_eds.plotbuffer import PlotBuffer
from pipeline_eds.cli import GLOBAL_SHUTDOWN_EVENT

logger = logging.getLogger(__name__)

PLOTLY_THEME = 'seaborn'
font_size = 20 if pyhabitat.on_termux() else 14

buffer_lock = threading.Lock()  # Optional, thread safety


# Placeholder for plot_buffer.get_all() data structure
class MockBuffer(PlotBuffer):
    """A PlotBuffer-backed mock buffer that implements the same interface as PlotBuffer.
    This ensures callers can use `is_empty()` and `get_all()` as expected.
    """
    def __init__(self):
        super().__init__(max_points=1000)
        sample = {
            "Series Alpha": {"x": [1, 2, 3, 4], "y": [7, 13, 7, 9], "unit": "MGD"},
            "Series Beta": {"x": [1, 2, 3, 4], "y": [10, 20, 15, 25], "unit": "MG/L"},
            "Series Gamma": {"x": [1, 2, 3, 4], "y": [5, 12, 11, 10], "unit": "MGD"},
            "Series Delta": {"x": [1, 2, 3, 4], "y": [12, 17, 14, 20], "unit": "MG/L"},
            "Series Epison": {"x": [1, 2, 3, 4], "y": [4500, 3000, 13000, 8000], "unit": "KW"},
            "Series Zeta": {"x": [1, 2, 3, 4], "y": [5000, 4000, 12000, 9000], "unit": "KW"},
        }
        for label, series in sample.items():
            # Ensure structure matches PlotBuffer.data entries
            self.data[label] = {"x": list(series["x"]), "y": list(series["y"]), "unit": series.get("unit")}

def assess_unit_stats(data):
    """
    For curves with shared units, determine the overall min/max for the shared axis
    """
    # --- PASS 1: AGGREGATE DATA RANGES PER UNIT ---
    # We must loop through all data first to find the true min/max for each unit.
    unit_stats = {}
    for label, series in data.items():
        # Clean unit string to ensure unique unit grouping
        unit = _clean_unit(series)

        y_data = [float(x) for x in series["y"]]
        if not y_data:
            continue

        current_min, current_max = min(y_data), max(y_data)

        if unit not in unit_stats:
            unit_stats[unit] = {"min": current_min, "max": current_max}
        else:
            # Update the min/max for this unit if needed
            unit_stats[unit]["min"] = min(unit_stats[unit]["min"], current_min)
            unit_stats[unit]["max"] = max(unit_stats[unit]["max"], current_max)
    return unit_stats

def assess_layout_updates(unit_stats):
    # --- BUILD AXES BASED ON AGGREGATED STATS ---
    # Now that we have the final range for each unit, create the axes.
    axis_counter = 0
    layout_updates = {}
    unit_to_axis_index = {}  # enables a new axis to be made for each unique unit
    annotations = []

    total_axes = len(unit_stats)

    for unit, stats in unit_stats.items():
        unit_to_axis_index[unit] = axis_counter
        layout_key = 'yaxis' if axis_counter == 0 else f'yaxis{axis_counter + 1}'

        def get_stat_range(stats):
            y_min=stats["min"]
            y_max=stats["max"]
            return (y_max, y_min)
        y_max,y_min = get_stat_range(stats)
        def check_for_boolean(y_max,y_min):
            if y_max==1 and y_min==0:
                logger.debug(f"{y_max=},{y_min=}")
                
        layout_updates[layout_key],annotation = build_y_axis(
            y_min=y_min,
            y_max=y_max,
            axis_index=axis_counter,
            axis_label=f"{unit}",
            total_axes=total_axes,
            tick_count=10,
            unit=unit
        )
        annotations.append(annotation)
        axis_counter += 1
    return layout_updates, unit_to_axis_index, annotations

def y_normalize_global(y_original,unit_stats, unit=None):
    # Get the global min/max for this trace's unit
    global_min = unit_stats[unit]["min"]
    global_max = unit_stats[unit]["max"]

    # VISUAL NORMALIZATION: Normalize using the GLOBAL range for the unit.
    # This ensures all traces on the same axis share the same scale.
    if global_max == global_min:
        y_normalized = [0.0] * len(y_original)

    else:
        range_val = global_max - global_min
        y_normalized = [
            (y_val - global_min) / range_val
            for y_val in y_original
        ]
    return y_normalized

def calculate_y_axis_offset_position(axis_index:int, total_axes:int=1):
    """
    Calculate the horizontal position (0.0 to 1.0) for a floating Y-axis,
    spreading 'total_axes' evenly across the entire plot domain.
    """
    #pos = (0.0025*axis_index**2)+(axis_index)*0.1
    if total_axes <= 1:
        return 0.0
    
    # Calculate step size based on how many total axes need to fit on the left
    pos = (axis_index / (total_axes - 1)) if total_axes > 1 else 0.0
    logger.debug(f"{axis_index=}, {total_axes=}, {pos=}")

    return pos


def build_y_axis(y_min, y_max,axis_index:int,axis_label:str,total_axes:int,tick_count:int = 10,unit:str|None=None):
    # Normalize the data and get min/max for original scale
    
    # Define the original tick values for each axis
    
    original_ticks = get_ticks_array_n(y_min,y_max,tick_count)
    
    # Calculate the normalized positions for the original ticks
    ticktext = [f"{t:.0f}" for t in original_ticks]
    tickvals=normalize_ticks(original_ticks, y_min, y_max) # Normalized positions

    pos = calculate_y_axis_offset_position(axis_index, total_axes=total_axes)
    
    overlaying_prop = "y" if axis_index > 0 else None
    
    yaxis_dict=dict(
        #title=dict(text=axis_label, standoff=10), # Use dict for better control
        title=None,
        overlaying = overlaying_prop,
        side="left",
        anchor="free", 
        #anchor="x", 
        position = pos,
        #range=[0, 1], # Set the axis range to the normalized data range
        #range = [-0.05, 1.05], # Set range for normalized data [0,1] with a little padding
        tickmode='array',
        tickvals = tickvals,
        ticktext=ticktext,           # Original labels
        showgrid=(axis_index == 0), # Show grid only for the first (leftmost) y-axis
        gridcolor='#e0e0e0',
        layer = "above traces",
        #layer = "below traces",
        zeroline=False
        ) 
    xshift = -35
    if axis_index == 0:
        xshift = 25
    annotation = dict(
            x=pos,
            y=0.93,
            yanchor="top",
            xref="paper",
            yref="paper",
            text=unit,
            showarrow=False,
            textangle=-90,
            #xanchor="right",
            xanchor="center",
            xshift=xshift,
            #yanchor="bottom",
        )
    return yaxis_dict, annotation

def _clean_unit(series):
    raw_unit = series.get("unit")
    return raw_unit.strip().upper() if raw_unit else "NULL"
    
def produce_plotly_figure(data):
    unit_stats = assess_unit_stats(data)
    #logger.debug(f"{unit_stats=}")
    layout_updates, unit_to_axis_index, annotations = assess_layout_updates(unit_stats)
    #logger.debug(f"{unit_to_axis_index=}")
    traces = []

    for i, (label, series) in enumerate(data.items()):
        y_original = [float(x) for x in series["y"]]
        unit = _clean_unit(series)
        
        # 1. VISUAL NORMALIZATION: Normalize y-data for plotting
        #y_normalized , y_min, y_max = normalize(y_original)
        #if y_original.size == 0: continue
        if len(y_original)==0: continue
        y_normalized = y_normalize_global(y_original,unit_stats, unit)

        current_axis_idx = unit_to_axis_index[unit]
        axis_id = 'y' if current_axis_idx == 0 else f'y{current_axis_idx+1}' # This is the Plotly trace axis *name* ('y1', 'y2', etc.)

        scatter_trace = go.Scatter(
            x=series["x"],
            y=y_normalized,  # Use normalized data for visual plotting
            mode="lines+markers",
            name=label,
            #legendgroup=unit, # this makes it possible to click on and off a group but not individual curves.
            #legendgrouptitle_text=unit,
            yaxis=axis_id, # Link this trace to its specific y-axis using the expected plotly jargon (e.g. 'y', 'y1', 'y2', 'y3', etc.) 

            # 2. NUMERICAL ACCURACY: Store original data for hover info
            customdata=y_original,
            hovertemplate=(
                f"<b>{label}</b><br>"
                "X: %{x}<br>"
                "Y: %{customdata:.4f}<extra></extra>" # Display original Y from customdata
            ),
            opacity=1.0
        )
        traces.append(scatter_trace)

    
    # --- Figure Creation and Layout Updates ---
    final_layout = {
        #'title': "EDS Data Plot (Static)", # shows large on mobile, not very useful
        'template':PLOTLY_THEME,
        'showlegend': True,
        # Set the plot area to span the full width of the figure as requested
        'xaxis': dict(domain=[0.0, 1.0], title="Time"),
        'font':dict(size=font_size),
        'legend': dict(
            orientation="h",        # <-- Optional: 'h' for horizontal, 'v' for vertical
            #yanchor="auto",
            y=0.5,
            #y=0.02,
            #xanchor="auto",
            #x=0.98, # Position legend in the top-left corner
            x=0.5,
            xanchor="center",
            #yanchor="bottom",
            yanchor="middle",
            bgcolor='rgba(255, 255, 255, 0.5)', # semi transparent background
            bordercolor='grey',
            borderwidth=1,
            #title="Curves"
        ),
        'margin': dict(l=5, r=5, t=5, b=5) # Add on;y a little padding around the whole figure - this increases the size compared to the default
    }

    # --- File Generation and Display ---
    final_layout.update(layout_updates)
    final_layout["annotations"] = annotations
    fig = go.Figure(data=traces, layout=go.Layout(final_layout))
    #add_plotly_buttons_to_fig(fig) # rather than injectiing html
    fig.update_layout(
        uirevision="static"
    )

    return fig

def add_plotly_buttons_to_fig(fig):
    """Update fig, rather than HTML"""
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=-1,
                x=0.98,
                y=-0.05, # Positions it relative to the plotting area
                buttons=[
                    dict(
                        label="Hide Legend",
                        method="relayout",
                        args=[{"showlegend": False}] # Natively updates layout properties
                    ),
                    dict(
                        label="Show Legend",
                        method="relayout",
                        args=[{"showlegend": True}]
                    )
                ]
            )
        ]
    )


def show_static(plot_buffer) -> "go.Plotly":
    """
    Renders the current contents of plot_buffer as a static HTML plot.
    - Data is visually normalized, but hover-text shows original values.
    - Each curve gets its own y-axis, evenly spaced horizontally.
    """
    if plot_buffer is None:
        print("plot_buffer is None")
        return

    with buffer_lock:
        data = plot_buffer.get_all()

    if not data:
        print("plot_buffer is empty")
        return

    fig = produce_plotly_figure(data)
    
    

    # 1. Create your temp file exactly as before
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        tmp_path = Path(f.name)

    #plot_config = {"editable": True} # doesnt seem to work
    plot_config = {
        "responsive": True,
        "displaylogo": False,
        "scrollZoom": True,
        "editable": False,
        "doubleClick": "reset",
        "modeBarButtonsToRemove": [
            "lasso2d",
            "select2d",
        ],
    }
    logger.debug(fig.layout.annotations)
    #fig.show()
    html = pio.to_html(
        fig,
        include_plotlyjs=True,
        full_html=True,
        config=plot_config,
    )
    html= inject_buttons(html)
    tmp_path.write_text(html)
    abs_path = tmp_path.resolve()

    # Standard desktop environments use direct file access
    if not pyhabitat.on_termux():
        webbrowser.open(abs_path.as_uri())
        return
    else:
        launch_file(str(abs_path))

    return

#def inject_buttons(tmp_path: Path) -> Path:
def inject_buttons(html_str: str) -> str:
    """
    Injects a shutdown button and corresponding JavaScript logic into the existing plot HTML file.
    Injects a darkmode button.
    Injects a button to hide the legend.
    """

    js_close_logic = """
    function closePlot() {
        if (window.location.protocol.startsWith('http')) {
            fetch('/shutdown')
                .then(() => {
                    console.log("Server shutdown requested.");
                    window.close(); 
                })
                .catch(error => {
                    console.error("Shutdown endpoint failed:", error);
                    window.close();
                });
        } else {
            console.log("Static file mode detected. Closing window.");
            window.close();
        }
    }
    """
    # ----------------------------------------------------
    # JavaScript for Plotly-specific controls
    # ----------------------------------------------------
    js_plotly_logic = f"""
    let isLegendVisible = true;

    function getPlotlyDiv() {{
        /** Plotly plots are typically contained in the first div with the class 'js-plotly-plot' **/
        return document.querySelector('.js-plotly-plot');
    }}

    function toggleLegend() {{
        const plotDiv = getPlotlyDiv();
        if (!plotDiv) return;

        isLegendVisible = !isLegendVisible;
        const newVisibility = isLegendVisible;
        const button = document.getElementById('toggleLegendButton');
        
        /** Update the Plotly layout **/
        Plotly.relayout(plotDiv, {{
            'showlegend': newVisibility
        }});

        /** Update the button text **/
        button.textContent = newVisibility ? 'Hide Legend' : 'Show Legend';
    }}


    function toggleTheme() {{
        const body = document.body;
        const button = document.getElementById('toggleThemeButton');

        // Toggle classes between theme-dark (inverted) and theme-light (native)
        if (body.classList.contains('theme-light')) {{
            body.classList.remove('theme-light');
            body.classList.add('theme-dark');
        }} else {{
            body.classList.remove('theme-dark');
            body.classList.add('theme-light');
        }}

        // Update button text to reflect the NEW mode it will switch TO
        button.textContent = body.classList.contains('theme-light') ? 'Dark Mode' : 'Light Mode';
    }}

    // --- Initialization: Set button text based on initial class ---
    (function() {{
        const button = document.getElementById('toggleThemeButton');
        if (button) {{
            // We start with <body class="theme-dark">, so the button should offer to switch to 'Light Mode'.
            button.textContent = 'Light Mode';
        }}
    }})();
    // -------------------------------------------------------------
    """
    # ----------------------------------------------------
    # Inject Buttons into the HTML
    # ----------------------------------------------------
    
    # Define the HTML/CSS for all control buttons
    buttons_html = f"""
    <style>
        .control-button {{
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            background-color: #3b82f6;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
            transition: background-color 0.3s;
            z-index: 1000;
            margin-left: 10px; /* Space between buttons */
        }}
        .control-button:hover {{
            background-color: #2563eb;
        }}
        #button-container {{
            position: fixed;
            bottom: 15px;
            right: 15px;
            display: flex;
            flex-direction: row-reverse; /* Arrange buttons from right (Close Plot) to left (Legend) */
            align-items: center;
        }}

        /* --- THEME STYLES --- */
        
        /* Transition for smooth visual changes */
        body, .js-plotly-plot {{
            transition: background-color 0.0s ease, color 0.0s ease, filter 0.0s ease;
        }}
        
        /* THEME DARK (Initial State) - Apply filter to invert the light Plotly output */
        body.theme-dark {{
            background-color: #111; /* Dark background for the page */
            color: #eee;
        }}
        body.theme-dark .js-plotly-plot {{
            /* Invert the colors of the light Plotly chart to make it dark */
            filter: invert(1) hue-rotate(180deg); 
            background-color: #111;
        }}

        /* THEME LIGHT (Toggled State) - Native Plotly look (seaborn is light) */
        body.theme-light {{
            background-color: #fafafa; /* Light background for the page */
            color: #222;
        }}
        body.theme-light .js-plotly-plot {{
            /* Remove filter to show native light Plotly colors */
            filter: none;
            background-color: #fafafa;
        }}

    </style>

    <div id="button-container">
        <button class="control-button" onclick="closePlot()">Close Plot</button>
        <button id="toggleThemeButton" class="control-button" onclick="toggleTheme()">Loading Theme...</button>
        <button id="toggleLegendButton" class="control-button" onclick="toggleLegend()">Hide Legend</button>
    </div>

    <script>
        {js_close_logic}
        {js_plotly_logic}
    </script>
    """

    # Read the existing Plotly HTML
    #html_content = tmp_path.read_text(encoding='utf-8')
    html_content=html_str

    # FIX: Replace <body> with <body class="theme-dark"> to trigger the dark (inverted) styles immediately
    html_content = html_content.replace('<body>', '<body class="theme-dark">')

    # Inject the button and script right before the closing </body> tag
    html_content = html_content.replace('</body>', buttons_html + '</body>')
    return html_content
    # Rewrite the file with the new content
    ##tmp_path.write_text(html_content, encoding='utf-8')
    # return tmp_path
    ##return # the path does not change

if __name__ == '__main__':
    # Add a signal handler for testing the CLI shutdown path (Ctrl+C)
    def handle_interrupt(sig, frame):
        """Signal handler for SIGINT (Ctrl+C)."""
        print("\n[Demo] Main process received CTRL+C. Setting shutdown flag...")
        GLOBAL_SHUTDOWN_EVENT.set()

    show_static(MockBuffer())
