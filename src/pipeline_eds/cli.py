# src/pipeline_eds/cli.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import sqlite3
from rich.table import Table
from rich.console import Console
from click import BadParameter 
import typer
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
import sys
import re
import pyhabitat as ph
import threading
from typer_helptree import add_typer_helptree
import logging
#print(f"DEBUG: Handlers present at start: {logging.getLogger().handlers}")

try:
    import colorama # explicitly added so for the shiv build
except ImportError:
    colorama = None  # or handle gracefully
try:
    import tzdata # explicitly added so for the shiv build
except ImportError:
    tzdata = None  # or handle gracefully

console = Console(stderr=True)

from .time_manager import TimeManager
from .create_sensors_db import get_db_connection, create_packaged_db, reset_user_db # get_user_db_path, ensure_user_db, 
from .server.trend_server_eds import launch_server_for_web_interface_eds_trend 
from .api.eds.rest.client import ClientEdsRest
from .api.eds.rest.config import get_eds_rest_api_credentials
from .security_and_config import get_external_api_credentials, init_security, CONFIG_PATH
from .api.eds.config import get_configurable_default_plant_name
from .termux_setup import setup_termux_integration, cleanup_termux_integration
from .windows_setup import setup_windows_integration, cleanup_windows_integration
from .helpers import nice_step,asses_time_range, iso_time
from .plotbuffer import PlotBuffer
from .version_info import  __version__, get_package_name
from .api.eds.rest.demo import demo_eds_webplot_point_live, demo_eds_save_point_export
from .api.eds.exceptions import  EdsLoginException
from .logging_setup import configure_logging_for_application


GLOBAL_SHUTDOWN_EVENT = threading.Event()

def handle_interrupt(sig, frame):
    """Signal handler for SIGINT (Ctrl+C)."""
    print("Main process received CTRL+C. Setting shutdown flag...")
    GLOBAL_SHUTDOWN_EVENT.set()
    # You may also want to propagate the signal to stop Uvicorn
    # If Uvicorn is in a separate thread/process, this handles the main script.

# Set the signal handler right after starting your server
import signal
#signal.signal(signal.SIGINT, handle_interrupt)

### Pipeline CLI
app = typer.Typer(name="pipeline-eds",
        help="CLI for running pipeline workspaces.",
        add_completion=False,)

add_typer_helptree(app=app, console=console, version = __version__,hidden=False)

@app.callback(invoke_without_command=True,no_args_is_help=True)
# @app.callback(invoke_without_command=False,no_args_is_help=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", is_flag=True, help="Show the version."),
    debug: bool = typer.Option(False, "--debug", "-d", is_flag=True, help="Enable diagnostic logging."),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True, help="Enable detail logging.")
    ):
    """
    Pipeline CLI – run workspaces built on the pipeline framework.
    """

    if version:
        typer.echo(__version__)
        raise typer.Exit(code=0)
    
    # If a user is specifically asking for CLI structures, don't re-wire logging handlers
    if ctx.invoked_subcommand in [None, "helptree", "help"]:
        if ctx.invoked_subcommand is None:
            launch_server_for_web_interface_eds_trend()
            raise typer.Exit()
        return
    # Configure logging immediately
    configure_logging_for_application(debug,verbose) 
    
    # Join the string from the command line arg and log debug to show the command.
    full_command_list = sys.argv
    command_string = " ".join(full_command_list)
    logging.debug(f"command:\n{command_string}\n")
    

@app.command(name="webapp", help="Show the GUI. Use the --web flag for a browser-based interface.")
def launch_webapp_eds_trend():
    """
    Allows GUI interaction with EDS Trend
    """
    launch_server_for_web_interface_eds_trend()
    
@app.command()
def list_sensors(
    db_path: str = None,
    reset: bool = typer.Option(False, "--reset", help = "Reset the database file from the code-embedded sensor data"),
    ):
    """ See a cheatsheet of commonly used sensors from the database."""
    if reset:
        packaged_db = create_packaged_db()
        user_db = reset_user_db(packaged_db)

    try:
        # db_path: str = "sensors.db"
        if db_path is not None:
            conn = sqlite3.connect(db_path)
        else:  
            conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT idcs, iess, zd, ovation_drop, units, description FROM sensors")
        rows = cur.fetchall()
        conn.close()
    except:
        # if fail, it is likely the use has an outdated db on their system. Force update, then run again.
        packaged_db = create_packaged_db()
        user_db = reset_user_db(packaged_db)
        if db_path is not None:
            conn = sqlite3.connect(db_path)
        else:  
            conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT idcs, iess, zd, ovation_drop, units, description FROM sensors")
        rows = cur.fetchall()
        conn.close()

    table = Table(title="Common Sensor Cheat Sheet (hard-coded)")
    table.add_column("IDCS", style="cyan")
    #table.add_column("IESS", style="magenta") # no reason to show this
    table.add_column("ZD", style="green")
    table.add_column("DROP", style="white")
    table.add_column("UNITS", style="white")
    table.add_column("DESCRIPTION", style="white")
    

    for idcs, iess, zd, ovation_drop, units, description in rows:
        table.add_row(idcs, zd, ovation_drop, units, description)
        

    console.print(table)
    logging.debug("⚠️ The ZD for the Stiles plant is WWTF", style = "magenta")

@app.command()
def live(
    idcs: list[str] = typer.Argument(..., help="Provide known idcs values that match the given zd."), # , "--idcs", "-i"
    zd: str = typer.Option('Maxson', "--zd", "-z", help = "Define the EDS ZD from your secrets file. This must correlate with your idcs point selection(s)."),
    force_webplot: bool = typer.Option(False,"--webplot","-w",help = "Use a web-based plot (plotly) instead of matplotlib. Useful for remote servers without display."),
    force_matplotlib: bool = typer.Option(False,"--matplotlib","-mpl",help = "Force matplotlib to be used for plotting. This will not work if matplotlib is not available.")
):
    """live data plotting, based on CSV query files. Coming soon - call any, like the 'trend' command."""
    console.print(f"Coming soon!")
    #demo_eds_webplot_point_live()

@app.command()
def trend(
    idcs: list[str] = typer.Argument(None, help="Provide known idcs values that match the given zd."), # , "--idcs", "-i"
    starttime: str = typer.Option(None, "--start", "-s", help="Identify start time. Use any reasonable format, to be parsed automatically. If you must use spaces, use quotes."),
    endtime: str = typer.Option(None, "--end", "-e", help="Identify end time. Use any reasonable format, to be parsed automatically. If you must use spaces, use quotes."),
    days: float = typer.Option(None, "--days", "-ds", help="Identify end time. Use any reasonable format, to be parsed automatically. If you must use spaces, use quotes."),
    plant_name: str = typer.Option(None, "--plantname", "-pn", help = "Provide the EDS ZD for your credentials."),
    print_csv: bool = typer.Option(False,"--print-csv","-p",help = "Print the CSV style for pasting into Excel."),
    seconds_between_points: int = typer.Option(None, "--seconds-between-points", "-sec", help="You can explicitly provide the delta between datapoints. If not, ~400 data points will be used, based on the nice_step() function."), 
    datapoint_count: int = typer.Option(None, "--datapoint-count", "-dp", help="You can explicitly provide the number of datapoints. Default: ~400 data points will be used, based on the nice_step() function. If the --datapoints flag is provided, the --step-seconds flag will be ignored. "), 
    force_webplot: bool = typer.Option(False,"--webplot","-w",help = "Use a browser-based plot instead of local (matplotlib). Useful for remote servers without display."),
    force_matplotlib: bool = typer.Option(False,"--matplotlib","-mpl",help="Force matplotlib to be used for plotting. This will not work if matplotlib is not available."),
    default_idcs: bool = typer.Option(False, "--default-idcs", "-d", help="Use the default IDCS values for the configured plant name, instead of providing them as arguments.")
    ):
    """
    Show a curve for a sensor over time.
    """

    init_security()

    #zd = api_credentials.get("zd")
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()

    # --- Conditional IDCS Input ---
    if idcs is None:
        if default_idcs:
            
            from pipeline_eds.api.eds.config import get_configurable_idcs_list
            # plant_name is resolved below, but we need a valid name for the helper
            # Temporarily resolve plant_name for the prompt if needed
            current_plant_name = plant_name if plant_name is not None else get_configurable_default_plant_name()
            idcs = get_configurable_idcs_list(current_plant_name)
            
            if not idcs:
                # Use a standard Typer error for missing config value
                raise BadParameter(
                    "The '--default-idcs' flag was used, but no IDCS points were configured or provided interactively.",
                    param_hint="--default-idcs"
                )
        else:
            # Raise a BadParameter exception to trigger the Typer/Rich error box
            error_message = (
                "\nIDCS values are required. You must either:\n"
                "1. Provide IDCS values as arguments: `eds trend IDCS1 IDCS2 ...`\n"
                "2. Use the default IDCS list: `eds trend --default-idcs`"
            )
            # This will now be wrapped in the structured error box.
            raise BadParameter(error_message, param_hint="IDCS...")
    # Convert all idcs values to uppercase, whether input now or stored in config. This assumes all IDCS value are uppcase all the time at every plant.
    idcs = [s.upper() for s in idcs]
    # --- END Conditional IDCS Input ---
    

    # Retrieve all necessary API credentials and config values.
    # This will prompt the user if any are missing.
    if isinstance(plant_name,str):
        api_credentials = get_eds_rest_api_credentials(plant_name=plant_name)
    if isinstance(plant_name,list):
        logging.debug("")
        logging.debug(f"/nMultiple plant names provided: {plant_name} ")
        logging.debug("Querying multiple plants at once not currently supported.") 
        logging.debug("Defaulting to use the first name.")
        api_credentials = get_eds_rest_api_credentials(plant_name=plant_name[0])
    
    logging.info(f"Data request processing...")
    logging.debug(f"plant_name = {plant_name}")

    idcs_to_iess_suffix = api_credentials.get("idcs_to_iess_suffix")
    iess_list = [x+idcs_to_iess_suffix for x in idcs]
    logging.debug(f"iess_list = {iess_list}")

    # Use the retrieved credentials to log in to the API, including custom session attributes
    try:
        session = ClientEdsRest.login_to_session_with_api_credentials(api_credentials)
    except RuntimeError as e:
        error_message = str(e)
        logging.warning(f"EDS login failed: {error_message}")
        return
    except Exception as e:
        logging.exception("Unexpected error during EDS login")
        return

    points_data = ClientEdsRest.get_points_metadata(session, filter_iess=iess_list)


    # --- Assess time range --
    dt_start, dt_finish = asses_time_range(starttime=starttime, endtime=endtime, days=days)

    # Should automatically choose time step granularity based on time length; map 
    if datapoint_count is not None: # ignore step_seconds if datapoint_count is provided
        # Ensure step_seconds is an integer, as required by the EDS API
        step_seconds = int((TimeManager(dt_finish).as_unix()-TimeManager(dt_start).as_unix())/datapoint_count)
    elif seconds_between_points is None and datapoint_count is None:
        step_seconds = nice_step(TimeManager(dt_finish).as_unix()-TimeManager(dt_start).as_unix()) # TimeManager(starttime).as_unix()
    elif seconds_between_points is not None and datapoint_count is None:
        step_seconds = seconds_between_points
    
    logging.debug(f"{session=}")
    logging.debug(f"{iess_list=}")
    logging.debug(f"{dt_start=}")
    logging.debug(f"{dt_finish=}")
    logging.debug(f"{step_seconds=}")

    results = ClientEdsRest.load_historic_data(session, iess_list, dt_start, dt_finish, step_seconds) 
    # results is a list of lists. Each inner list is a separate curve.
    if not results:
        logging.error("No results returned from API; terminating.")
        return typer.Exit(1)
    
    # The PlotBuffer instance is created once, outside the loop.
    data_buffer = PlotBuffer() 
    for idx, rows in enumerate(results):
        
        # We create a unique label for each of the 'rows' in the outer loop.
        # The plot will use this label to draw a separate line for each 'rows'.
        
        attributes = points_data[iess_list[idx]]
        unit = attributes.get('UN')
        label = f"{idcs[idx]}, {attributes.get('DESC')}, ({attributes.get('UN')})"
        #label = f"{idcs[idx]}, {attributes.get('DESC')}"
        
        #label = idcs[idx]
        
        # The raw from ClientEdsRest.get_tabular_trend() is brought in like this: 
        #   sample = [1757763000, 48.93896783431371, 'G'] 
        #   and then is converted to a dictionary with keys: ts, value, quality
        
        for row in rows:
            ts = iso_time(row.get("ts"))
            av = row.get("value")
            
            # All data is appended to the *same* data_buffer,
            # but the unique 'label' tells the buffer which series it belongs to.
            data_buffer.append(label, ts, av, unit)

    # Once the loop is done, you can call your show_static function
    # with the single, populated data_buffer.

    if force_matplotlib and not ph.matplotlib_is_available_for_gui_plotting():
        logging.debug(f"force_matplotlib = {force_matplotlib}, but matplotlib is not available. Plotly, web-based plotting will be used.\n")
    
    if force_webplot or not force_matplotlib or not ph.matplotlib_is_available_for_gui_plotting():
        from pipeline_eds import gui_plotly_static
        #gui_starlette_msgspec_plotly.run_gui(data_buffer)
        gui_plotly_static.show_static(data_buffer)
    elif ph.matplotlib_is_available_for_gui_plotting():
        from pipeline_eds import gui_mpl_live
        #gui_mpl_live.run_gui(data_buffer)
        gui_mpl_live.show_static(data_buffer)
    
    if print_csv:
        print(f"Time,\\{iess_list[0]}\\,")
        for idx, rows in enumerate(results):
            for row in rows:
                print(f"{iso_time(row.get('ts'))},{row.get('value')},")

@app.command(name="config", help="Configure and store API and database credentials.")
def configure_credentials(
    overwrite: bool = typer.Option(False, "--overwrite", "-o", help="Overwrite existing credentials, with confirmation protection."),
    textedit: bool = typer.Option(False, "--textedit", "-t", help = "Open the config file in a text editor instead of using the guided prompt.")
    ):
    """
    Guides the user through a guided credential setup process. This is not necessary, as necessary credentials will be prompted for as needed, but this is a convenient way to set up multiple credentials at once. This command with the `--overwrite` flag is the designed way to edit existing credentials.
    """
    if textedit:
        logging.debug(F"Config filepath: {CONFIG_PATH}")
        ph.edit_textfile(CONFIG_PATH)
        return
            
    console.print("")
    console.print("--- Pipeline-EDS Credential Setup ---")
    #console.print("This will securely store your credentials in the system keyring and a local config file.")
    console.print("You can skip any step by saying 'no' or 'n' when prompted.")
    console.print("You can quit editing credentials at any time by escaping with `control+C`.")
    console.print("You can run this command again later to add or modify credentials.")
    console.print("If you are not prompted for a credential, it is likely already configured. To change it, use the --overwrite flag.")
    console.print("")
    if overwrite:
        console.print("⚠️ Overwrite mode is enabled. Existing credentials will shown and you will be prompted to confirm overwriting them.")
        console.print(f"Alternatively, edit the configuration file directly in a text editor with the `--textedit` flag.")
        console.print(f"Config file path: {CONFIG_PATH}", style=typer.colors.MAGENTA)   

    # Get a list of plant names from the user
    #num_plants = typer.prompt("How many EDS plants do you want to configure?", type=int, default=1)
    num_plants = 1
    plant_names = []
    for i in range(num_plants):
        plant_name = typer.prompt(f"Enter a unique name for Plant (e.g., 'Maxson' or 'Stiles')")
        plant_names.append(plant_name)

    # Loop through each plant to configure its credentials
    for name in plant_names:
        console.print(f"\nConfiguring credentials for {name}...")
        
        # Configure API for this plant
        if typer.confirm(f"Do you want to configure the EDS API for '{name}'?", default=True):
            get_eds_rest_api_credentials(plant_name=name, overwrite=overwrite)

    # Configure any other external APIs
    if False and typer.confirm("Do you want to configure external API credentials? (e.g., RJN)"):
        external_api_name = typer.prompt("Enter a name for the external API (e.g., 'RJN')")
        get_external_api_credentials(party_name=external_api_name, overwrite=overwrite)

    console.print("\nSetup complete. You can now use the commands that require these credentials.")
    console.print("If a question was skipped, it is because the credential is already configured.")
    console.print("Run this command again with --overwrite to change it.")

@app.command(name="setup", help="Setup touch point like widget entries, context menu items, and AppData folder for system integration. Based on environment.")
def setup_integration(
    uninstall: bool = typer.Option(False,"--uninstall","-un",help = "Remove the installation artifacts for the current operating system."),
    upgrade: bool = typer.Option(False, "--upgrade", "-up", help = "Uppgrades will be forece, namely shortcut scripts on Termux will be overwritten even if they already exist."),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Show debugging output and do not actually perform any installation or uninstallation actions.")
):
    """
    Windows: Un/install the registry context-menu item, the launcher BAT, and the AppData folder
    Termux: Add / remove the scripts from the .shortcuts/ folder.
    """

    if debug:
        # is_win_exe(debug=True) # inferred, not yet implemented
        ph.is_pipx(debug=True)
        ph.is_pyz(debug=True)
        ph.is_elf(debug=True)
        return
    
    if uninstall:
        if ph.on_windows():
            if typer.confirm("Are you sure you want to uninstall the registry context-menu item, the launcher BAT, and empty out the AppData folder?"):
                cleanup_windows_integration()
        elif ph.on_termux():
            cleanup_termux_integration()
        return

    if ph.on_windows():
        console.print("AppData will be set up explicity and a content menu item will be added to your Registry.")
        setup_windows_integration()
    elif ph.on_termux():
        console.print("Scripts will now be added to the $HOME/.shortcuts/ directory for launching from the Termux Widget.")
        setup_termux_integration(force=upgrade)
        console.print("Update complete.")
        console.print(f"\n{get_package_name()} --version")
        typer.secho(f"{get_package_name()} {__version__}", fg=typer.colors.GREEN, bold=True)
        console.print("\n")
        input("Press Enter to exit...") # moved to internal of setup_termux_integration()

@app.command()
def points_export(
    export_path: str = typer.Argument(None, help = "Provide a specific export path. If not provided, the export will be saved to the current working directory."),
    plant_name: str = typer.Option(None, "--plantname", "-pn", help = "Provide the EDS ZD for your credentials."),
    #filter_idcs: str = typer.Option(None,"--idcs", "-i", help="Provide known idcs values to filter the export."), # , "--idcs", "-i"
):
    """
    Export a list of all EDS Points. This is specific to the EDS.
    """
    filter_idcs=None # trouble getting multiple points back, suppress for now
    if plant_name is None:
        plant_name = get_configurable_default_plant_name()


    if isinstance(plant_name,str):
        api_credentials = get_eds_rest_api_credentials(plant_name=plant_name)

    if isinstance(plant_name,list):
        logging.debug("")
        logging.debug(f"Multiple plant names provided: {plant_name} ")
        logging.debug("Querying multiple plants at once currently supported.") 
        logging.debug("Defaulting to use the first name.")
        api_credentials = get_eds_rest_api_credentials(plant_name=plant_name[0])
    
    # Use the retrieved credentials to log in to the API, including custom session attributes
    logging.debug("Logging in to session...")
    try:
        session = ClientEdsRest.login_to_session_with_api_credentials(api_credentials)
    except RuntimeError as e:
        error_message = str(e)
        logging.warning(f"EDS login failed: {error_message}")
        return
    except Exception as e:
        logging.exception("Unexpected error during EDS login")
        return

    logging.debug("Retrieving point export...")
    if filter_idcs is not None:
        filter_idcs_list = re.split(r'[,\s]+', filter_idcs)
        idcs_to_iess_suffix = api_credentials.get("idcs_to_iess_suffix")
        filter_iess = [x+idcs_to_iess_suffix for x in filter_idcs_list]
        logging.debug(f"filter_iess = {filter_iess}")
    else:
        filter_iess = None
    point_export_decoded_str = ClientEdsRest.get_points_export(session, filter_iess = filter_iess)

    logging.debug("Saving export file...")
    app_dir_name = f".{get_package_name()}"
    if export_path is None:
        data_dir = Path.home() / app_dir_name / "data" 
        data_dir.mkdir(parents=True, exist_ok=True)
        #now_time_str = TimeManager(TimeManager.now()).as_safe_isoformat_for_filename()
        now_time_str = TimeManager.now().as_safe_isoformat_for_filename()
        export_path = data_dir / f'{plant_name}-export_eds_points_{now_time_str}.txt'
    try:
        ClientEdsRest.save_points_export(point_export_decoded_str, export_path = export_path)
    except Exception as e: # Catch the actual save errors here
        logging.debug(f"ERROR: Failed to save export file to: {export_path}")
        logging.debug(f"Details: {e}")
        return
    console.print(f"\nExport file saved to: \n{export_path}\n")

if __name__ == "__main__":
    app()
