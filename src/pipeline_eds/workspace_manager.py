# src/pipeline_eds/workspace_manager.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import os
import toml
import logging
from pathlib import Path
import sys

'''
Goal:
Implement default-workspace.toml variable: use-most-recently-edited-workspace-directory 
'''

logger = logging.getLogger(__name__)

class WorkspaceManager:
    # It has been chosen to not make the WorkspaceManager a singleton if there is to be batch processing.

    WORKSPACES_DIR_NAME = 'workspaces'
    QUERIES_DIR_NAME = 'queries' # generate em
    IMPORTS_DIR_NAME = 'imports'
    EXPORTS_DIR_NAME = 'exports'
    SCRIPTS_DIR_NAME = 'scripts'
    CONFIGURATIONS_DIR_NAME = 'configurations'
    LOGS_DIR_NAME = 'logs'
    CONFIGURATION_FILE_NAME = 'configuration.toml'
    APP_NAME = "pipeline_eds"

    TIMESTAMPS_JSON_FILE_NAME = 'timestamps_success.json'

    # Detect if running in a dev repo vs installed package
    if getattr(sys, "frozen", False):
        # Running from a pipx/executable environment
        ROOT_DIR = None
    else:
        # Running from a cloned repo
        ROOT_DIR = Path(__file__).resolve().parents[2]  # root directory
    
    # This climbs out of /src/pipeline_eds/ to find the root.
    # parents[0] → The directory that contains the (this) Python file.
    # parents[1] → The parent of that directory.
    # parents[2] → The grandparent directory (which should be the root), if root_pipeline\src\pipeline\
    # This organization anticipates PyPi packaging.
    
    def __init__(self, workspace_name):
        self.workspace_name = workspace_name
        self.workspaces_dir = self.get_workspaces_dir()
        self.workspace_dir = self.get_workspace_dir()
        self.configurations_dir = self.get_configurations_dir()
        self.exports_dir = self.get_exports_dir()
        self.imports_dir = self.get_imports_dir()
        self.queries_dir = self.get_queries_dir()
        self.scripts_dir = self.get_scripts_dir()
        self.logs_dir = self.get_logs_dir()
        self.aggregate_dir = self.get_aggregate_dir()

        
        self.check_and_create_dirs(list_dirs = 
                                    [self.workspace_dir, 
                                    self.exports_dir, 
                                    self.imports_dir, 
                                    self.scripts_dir, 
                                    self.logs_dir,
                                    self.aggregate_dir])

    
    @classmethod
    def get_workspaces_dir(cls):
        """
        Return workspaces directory depending on environment:
        - If ROOT_DIR is defined (repo clone), use that
        - Else use AppData/local platform-specific location
        """
        if cls.ROOT_DIR and (cls.ROOT_DIR / cls.WORKSPACES_DIR_NAME).exists():
            workspaces_dir = cls.ROOT_DIR / cls.WORKSPACES_DIR_NAME
        else:
            workspaces_dir = cls.get_appdata_dir() / cls.WORKSPACES_DIR_NAME
            workspaces_dir.mkdir(parents=True, exist_ok=True)
        return workspaces_dir
    
    @classmethod
    def most_recent_workspace_name(cls):
        workspaces_dir = cls.get_workspaces_dir()
        all_dirs = [p for p in workspaces_dir.iterdir() if p.is_dir() and not p.name.startswith('.')]
        if not all_dirs:
            return None
        latest = max(all_dirs, key=lambda p: p.stat().st_mtime)
        return latest.name

    def get_workspace_dir(self):
        # workspace_name is established at instantiation. You want a new name? Initialize a new WorkspaceManager(). It manages one workpspace.
        return self.get_workspaces_dir() / self.workspace_name 

    def get_exports_dir(self):
        return self.workspace_dir / self.EXPORTS_DIR_NAME
    
    def get_exports_file_path(self, filename):
        # Return the full path to the export file
        return self.exports_dir / filename

    def get_aggregate_dir(self):
        # This is for five-minute aggregation data to be stored between hourly bulk passes
        # This should become defunct once the tabular trend data request is functional 
        return self.exports_dir / 'aggregate'
    
    def get_configurations_dir(self):
        return self.workspace_dir / self.CONFIGURATIONS_DIR_NAME
    
    def get_configuration_file_path(self):
        # Return the full path to the config file or create it from the fallback copy if it exists
        file_path = self.get_configurations_dir() / self.CONFIGURATION_FILE_NAME
        return file_path
    
    
    def get_logs_dir(self):
        return self.workspace_dir / self.LOGS_DIR_NAME

    def get_imports_dir(self):
        return self.workspace_dir / self.IMPORTS_DIR_NAME

    def get_imports_file_path(self, filename):
        # Return the full path to the export file
        return self.imports_dir / filename
        
    def get_scripts_dir(self):
        return self.workspace_dir / self.SCRIPTS_DIR_NAME

    def get_scripts_file_path(self, filename):
        # Return the full path to the config file
        return self.get_scripts_dir() / filename
    
    def get_queries_dir(self):
        return self.workspace_dir / self.QUERIES_DIR_NAME
    
    def get_queries_file_path(self,filename): #
        # Return the full path to the config file
        filepath = self.get_queries_dir() / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Query filepath={filepath} not found. \nPossible reason: You are in the wrong project directory.")
        return filepath    
    
    def get_timestamp_success_file_path(self):
        # Return the full path to the timestamp file
        filepath = self.get_queries_dir() / self.TIMESTAMPS_JSON_FILE_NAME
        logger.info(f"WorkspaceManager.get_timestamp_success_file_path() = {filepath}")
        return filepath

    def check_and_create_dirs(self, list_dirs):
        for dir_path in list_dirs:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def identify_default_workspace_path(cls):
        """
        Class method that reads default-workspace.toml to identify the default-workspace path.
        """

        workspaces_dir = cls.get_workspaces_dir()
        workspace_name = cls.identify_default_workspace_name()
        if workspace_name is None:
            workspace_name = cls.most_recent_workspace_name() # if 
        if workspace_name is None:
            workspace_name = 'eds'    

        workspace_path = workspaces_dir / workspace_name
        if not workspace_path.exists():
            workspace_path.mkdir(parents=True, exist_ok=True)
            
        return workspace_path
    
    @classmethod
    def identify_default_workspace_name(cls):
        """
        Class method that reads default-workspace.toml to identify the default-workspace.
        """
        from dworshak_env import DworshakEnv
        env_mngr = DworshakEnv()
        try:
            return env_mngr.get("DEFAULT_WORKSPACE")
        except Exception as e:
            logger.debug(f"identify_default_workspace_name() failed: {e}")
            return cls.most_recent_workspace_name() or "default"


        
    def get_default_query_file_paths_list(self):
        
        default_query_path = self.get_queries_dir()/ 'default-queries.toml'
        
        with open(default_query_path, 'r') as f:
            query_config = toml.load(f)
        if 'default-query' not in query_config or 'files' not in query_config['default-query']:
            raise ValueError("Missing ['default-query']['files'] in default-queries.toml")
        filenames = query_config['default-query']['files']
        if not isinstance(filenames, list):
            raise ValueError("Expected a list under ['default-query']['files'] in default-queries.toml")
        paths = [self.get_queries_file_path(fname) for fname in filenames]

        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Query file not found: {path}")
        return paths

    @property
    def name(self):
        return self.workspace_name
    
    @classmethod
    def get_appdata_dir(cls) -> Path:
        """Return platform-appropriate appdata folder."""
        if os.name == "nt":  # Windows
            base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) ## configuration-example
        elif os.name == "posix" and "ANDROID_ROOT" in os.environ:  # Termux
            base = Path.home() / ".local" / "share"
        else:  # macOS/Linux
            base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return base / cls.APP_NAME

def establish_default_workspace():
    workspace_name = WorkspaceManager.identify_default_workspace_name()
    logger.info(f"workspace_name = {workspace_name}")
    workspace_manager = WorkspaceManager(workspace_name)
    logger.info(f"WorkspaceManager.get_workspace_dir() = {WorkspaceManager.get_workspace_dir()}")
    return 

def demo_establish_default_workspace():
    establish_default_workspace()

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "default"

    if cmd == "demo-default":
        demo_establish_default_workspace()
    else:
        print("Usage options: \n" 
        "uv run python -m pipeline_eds.api.eds demo-default \n")  

    
