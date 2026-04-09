#env.__main__.py
from __future__ import annotations # Delays annotation evaluation, allowing modern 3.10+ type syntax and forward references in older Python versions 3.8 and 3.9
import yaml

'''
migrate this to ConfigurationManager
'''

class SecretConfig:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def load_config(secrets_file_path): 
        with open(secrets_file_path, 'r') as f:
            return yaml.safe_load(f)
        
    def print_config(self):
        # Print the values
        for section, values in self.config.items():
            print(f"[{section}]")
            for key, val in values.items():
                print(f"{key} = {val}")


