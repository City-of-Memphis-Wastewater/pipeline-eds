# src/pipeline_eds/core/eds.py
"""
This was placed here by Grok.
Yes, we need a core directory, but for eds stuff we should be calling pipeline_eds.api.eds...
"""
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9import time
import plotly.offline as pyo # You'll need this for the desktop display
import webbrowser
from pathlib import Path
import os
import tempfile
import pyhabitat as ph 
from typer import BadParameter
import logging

from pipeline_eds.api.eds.soap.client import ClientEdsSoap
logger = logging.getLogger(__name__)

from pipeline_eds.api.eds.config import (APIProtocol, 
                                         get_configurable_default_plant_name, 
                                         get_configurable_idcs_list, 
                                         get_configurable_default_api_protocol
)
from pipeline_eds.api.eds.rest.config import get_eds_rest_api_credentials
from pipeline_eds.helpers import PlotType, nice_step, assess_time_range, iso_time
from pipeline_eds.time_manager import TimeManager
from pipeline_eds.plotbuffer import PlotBuffer
from pipeline_eds.api.eds.rest.client import ClientEdsRest
from pipeline_eds.api.eds.config import get_idcs_to_iess_suffix 

from pathlib import Path
from typer import BadParameter

def parse_idcs_input(value: list[str] | str | None) -> list[str]:
    """
    Parses inputs into a clean list of uppercase IDCS tags.
    Handles:
    - Space-separated: ["m100fi", "fi8001"]
    - Comma-separated: ["m100fi,fi8001"]
    - Mixed/Files: ["queries/wetwell.txt", "m100fi,fi8001"]
    """
    if not value:
        return []

    raw_lines: list[str] = []

    # Normalize inputs into lines or tokens
    items = [value] if isinstance(value, str) else value

    for item in items:
        path = Path(item)
        if path.is_file():
            try:
                raw_lines.extend(path.read_text().splitlines())
            except Exception as e:
                logger.error(f"Failed to read file '{path}': {e}")
        else:
            raw_lines.extend(item.splitlines())

    cleaned_points = []
    for line in raw_lines:
        line_str = line.strip()

        # Ignore empty lines and comment lines
        if not line_str or line_str.startswith("#"):
            continue

        # Strip inline comments
        if "#" in line_str:
            line_str = line_str.split("#")[0].strip()

        # Replace commas with spaces so split() handles both separators
        tokens = line_str.replace(",", " ").split()
        for token in tokens:
            t = token.strip().rstrip(",")
            if t:
                cleaned_points.append(t.upper())

    return cleaned_points


def resolve_idcs_list(idcs: list[str] | None, plant_name: str) -> list[str]:
    """
    Resolves the final list of IDCS points from CLI arguments, query files, or plant defaults.
    """
    if plant_name is not None:
        plant_name = get_configurable_default_plant_name()

    parsed_idcs = parse_idcs_input(idcs) if idcs else []

    if not parsed_idcs:
    
        error_message = (
            "\nIDCS values are required. You must either:\n"
            "1. Provide points or a query file: `eds trend m100fi fi8001` or `eds trend queries/wetwell.txt`\n"
            "2. Use the default IDCS list: `eds trend --default-idcs`"
        )
        raise BadParameter(error_message, param_hint="IDCS...")

    return parsed_idcs

def convert_static_historic_data_results_to_data_buffer(
    results: list,
    idcs: list[str],
    iess_list: list[str],
    points_data: dict
) -> PlotBuffer:
    """Helper to map raw API result rows into a structured PlotBuffer."""
    data_buffer = PlotBuffer() 
    for idx, rows in enumerate(results):
        iess_key = iess_list[idx]
        attributes = points_data.get(iess_key, {})
        
        unit = attributes.get('UN', 'N/A')
        description = attributes.get('DESC', 'Unknown Sensor')
        label = f"{idcs[idx]}, {description}, ({unit})"
        
        for row in rows:
            ts = iso_time(row.get("ts"))
            av = row.get("value")
            data_buffer.append(label, ts, av, unit)
            
    return data_buffer

def fetch_trend_data(
    idcs: list[str] | None, 
    starttime: str | None = None, 
    endtime: str | None = None, 
    days: float | None = None, 
    plant_name: str | None = None,
    seconds_between_points: int | None = None, 
    datapoint_count: int | None = None,
    default_idcs: bool = False,
    use_mock: bool = False,
    api_protocol: APIProtocol = APIProtocol.REST
) -> tuple[PlotBuffer, list, list[str], str]:
    """
    Core logic to fetch trend data from EDS API.
    Returns: (data_buffer, raw_results, idcs, plant_name)
    """
    # 1. Resolve Plant Name
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()
    elif isinstance(plant_name, list):
        logger.debug(f"\nMultiple plant names provided: {plant_name}")
        logger.debug("Querying multiple plants at once not currently supported. Defaulting to first name.")
        plant_name = plant_name[0]

    # 2. Handle Mock Request
    if use_mock:
        try:
            from pipeline_eds.gui_plotly_static import MockBuffer
            return MockBuffer(), [], [], plant_name
        except Exception:
            return PlotBuffer(), [], [], plant_name

    # 3. Resolve IDCS List
    if default_idcs:
        idcs = get_configurable_idcs_list(plant_name)
        if not idcs:
            raise BadParameter(
                "The '--default-idcs' flag was used, but no IDCS points were configured.",
                param_hint="--default-idcs"
            )
    else:
        idcs = resolve_idcs_list(idcs, plant_name)
        logger.debug(f"idcs={idcs}")

    if not idcs:
        return PlotBuffer(), [], [], plant_name

    # 4. Resolve Credentials & Client
    api_credentials = get_eds_rest_api_credentials(plant_name=plant_name)
    idcs_to_iess_suffix = api_credentials.get("idcs_to_iess_suffix")
    if idcs_to_iess_suffix is None:
        idcs_to_iess_suffix = get_idcs_to_iess_suffix(plant_name=plant_name)

    iess_list = [x + idcs_to_iess_suffix for x in idcs]
    logger.debug(f"iess_list = {iess_list}")

    if api_protocol == APIProtocol.REST:
        client_cls = ClientEdsRest
    elif api_protocol == APIProtocol.SOAP:
        client_cls = ClientEdsSoap
    else:
        raise ValueError(f"api_protocol {api_protocol} not accepted")

    # 5. Login
    try:
        session = client_cls.login_to_session_with_api_credentials(api_credentials)
    except RuntimeError as e:
        logger.warning(f"EDS login failed: {e}")
        return PlotBuffer(), [], idcs, plant_name
    except Exception:
        logger.exception("Unexpected error during EDS login")
        return PlotBuffer(), [], idcs, plant_name

    # 6. Metadata & Time Range Resolution
    points_data = client_cls.get_points_metadata(session, filter_iess=iess_list) or {}
    dt_start, dt_finish = assess_time_range(starttime=starttime, endtime=endtime, days=days)

    # 7. Step Seconds Calculation
    time_delta_seconds = TimeManager(dt_finish).as_unix() - TimeManager(dt_start).as_unix()
    if datapoint_count is not None and datapoint_count > 0: 
        step_seconds = max(1, int(time_delta_seconds / datapoint_count))
    elif seconds_between_points is not None:
        step_seconds = seconds_between_points
    else:
        step_seconds = nice_step(time_delta_seconds)

    logger.debug(f"{session=}")
    logger.debug(f"{iess_list=}")
    logger.debug(f"{dt_start=}")
    logger.debug(f"{dt_finish=}")
    logger.debug(f"{step_seconds=}")

    # 8. Load Historic Data
    results = client_cls.load_historic_data(session, iess_list, dt_start, dt_finish, step_seconds) 
    if not results:
        return PlotBuffer(), [], idcs, plant_name

    # 9. Data Conversion
    data_buffer = convert_static_historic_data_results_to_data_buffer(
        results, idcs, iess_list, points_data
    )
    return data_buffer, results, idcs, plant_name

def resolve_plotting_strategy(
    force_webplot: bool = False, 
    force_matplotlib: bool = False, 
    plot_type: PlotType | None = None
) -> PlotType:
    """
    Determines whether to use WEB (Plotly) or MPL (Matplotlib).
    Defaults to WEB (Plotly) unless force_matplotlib is requested.
    """
    # Explicit plot_type override (e.g., from web API/server payloads)
    if plot_type is not None:
        if plot_type == PlotType.MPL and not ph.matplotlib_is_available_for_gui_plotting():
            logger.warning("Matplotlib requested, but not available in environment. Falling back to Web/Plotly.")
            return PlotType.WEB
        return plot_type

    # Explicit CLI flag to force Matplotlib
    if force_matplotlib:
        if ph.matplotlib_is_available_for_gui_plotting():
            return PlotType.MPL
        logger.warning("force_matplotlib requested, but matplotlib is unavailable. Falling back to Web/Plotly.")
        return PlotType.WEB

    # Default fallback: always WEB (Plotly)
    return PlotType.WEB

def plot_trend_data(
    data_buffer: PlotBuffer, 
    force_webplot: bool = False, 
    force_matplotlib: bool = False,
    plot_type: PlotType | None = None
) -> None:
    """
    Handles common dispatching logic for plotting data buffer series based on strategy flags.
    """
    if data_buffer.is_empty():
        logger.warning("Attempted to plot empty PlotBuffer.")
        return

    # Resolve strategy into an explicit PlotType enum
    target_plot_type = resolve_plotting_strategy(
        force_webplot=force_webplot,
        force_matplotlib=force_matplotlib,
        plot_type=plot_type
    )

    # Multiplex rendering based on resolved PlotType
    if target_plot_type == PlotType.WEB:
        from pipeline_eds import gui_plotly_static
        gui_plotly_static.show_static(data_buffer)

    elif target_plot_type == PlotType.MPL:
        from pipeline_eds import gui_mpl_live
        gui_mpl_live.show_static(data_buffer)

    else:
        logger.error(f"Unsupported plot target type: {target_plot_type}")