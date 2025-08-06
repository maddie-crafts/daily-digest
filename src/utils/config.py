import yaml
import os
import re
from typing import Dict, Any, List

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._load_env_file()  # Load .env file first
        self._config = self._load_config()
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        env_path = os.path.join(os.path.dirname(self.config_path), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            # Remove quotes if present
                            value = value.strip('"\'')
                            os.environ[key] = value
    
    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_content = file.read()
                # Substitute environment variables
                config_content = self._substitute_env_vars(config_content)
                return yaml.safe_load(config_content)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")
    
    def _substitute_env_vars(self, content: str) -> str:
        """Replace ${VAR_NAME} with environment variable values"""
        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Return original if not found
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, content)
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_sources(self) -> List[Dict[str, Any]]:
        return self.get('sources', [])
    
    def get_scraping_config(self) -> Dict[str, Any]:
        return self.get('scraping', {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        return self.get('processing', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        return self.get('database', {})
    
    def get_web_config(self) -> Dict[str, Any]:
        return self.get('web', {})
    
    def get_scheduling_config(self) -> Dict[str, Any]:
        return self.get('scheduling', {})
    
    def get_email_config(self) -> Dict[str, Any]:
        return self.get('email', {})

def get_config() -> Config:
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    return Config(config_path)