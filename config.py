import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from logger import get_logger

class ConfigManager:
    """
    Simple configuration management for the enhanced video generation system.
    Provides flat key-value structure with environment variable resolution.
    """
    
    def __init__(self, config_path: str = "autopost_config.enhanced.json"):
        self.config_path = config_path
        self.logger = get_logger('config')
        self.config = {}
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file with environment variable resolution."""
        try:
            self.logger.info(f"Loading configuration from {self.config_path}")
            
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Config file {self.config_path} not found. Creating default configuration.")
                self.create_default_config()
            
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            
            # Resolve environment variables
            self.config = self.resolve_environment_variables(self.config)
            
            # Validate configuration
            self.validate_config()
            
            self.logger.info("Configuration loaded successfully")
            return self.config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def resolve_environment_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Replace ${ENV_VAR} placeholders with actual environment variable values."""
        resolved_config = {}
        
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]  # Remove ${ and }
                env_value = os.getenv(env_var)
                if env_value:
                    resolved_config[key] = env_value
                    self.logger.debug(f"Resolved {key} from environment variable {env_var}")
                else:
                    self.logger.warning(f"Environment variable {env_var} not set for {key}")
                    resolved_config[key] = value  # Keep original placeholder
            else:
                resolved_config[key] = value
        
        return resolved_config
    
    def create_default_config(self):
        """Create a default configuration file with placeholders."""
        default_config = {
            # Instagram Configuration
            "instagram_app_id": "${FB_APP_ID}",
            "instagram_app_secret": "${FB_APP_SECRET}",
            "instagram_user_id": "${INSTAGRAM_USER_ID}",
            "instagram_access_token": "${INSTAGRAM_ACCESS_TOKEN}",
            "instagram_token_expiration": "2025-08-23 21:00:33",
            "instagram_days_before_refresh": 7,
            
            # GCS Configuration
            "gcs_bucket": "autopot1-printdump",
            "gcs_api_key_path": "${GCS_API_KEY_PATH}",
            "gcs_folders": ["video_uploads", "music_uploads", "completed_works", "wip_photos", "build_photos"],
            "gcs_draft_folder": "draft_videos",
            
            # OpenAI Configuration
            "openai_api_key": "${OPENAI_API_KEY}",
            "gpt_assistant_id": None,
            "gpt_thread_id": None,
            "gpt_creation_prompt": "You are a creative AI assistant for 3D printing pottery content.",
            
            # JSON2Video Configuration
            "json2video_api_key": "${JSON2VIDEO_API_KEY}",
            "json2video_base_url": "https://api.json2video.com/v2",
            "json2video_timeout": 300,
            
            # Google Sheets Configuration
            "sheets_spreadsheet_id": "${GOOGLE_SHEETS_ID}",
            "sheets_credentials_path": "${GOOGLE_CREDENTIALS_PATH}",
            
            # Auto-posting Configuration
            "autopost_timeout": 300,
            "autopost_poll_interval": 30,
            
            # Logging Configuration (all optional - defaults to terminal output)
            "log_level": "INFO",
            "log_file": None,
            "log_max_size": "10MB",
            "log_backup_count": 5,
            "log_console_output": True
        }
        
        # Ensure directory exists
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        self.logger.info(f"Default configuration created at {self.config_path}")
        self.config = default_config
    
    def validate_config(self):
        """Basic validation of required configuration sections."""
        required_sections = [
            'instagram_app_id', 'instagram_app_secret', 'instagram_user_id', 'instagram_access_token',
            'gcs_bucket', 'gcs_api_key_path',
            'openai_api_key',
            'json2video_api_key'
        ]
        
        missing_fields = []
        for field in required_sections:
            if not self.config.get(field) or self.config[field] == f"${{{field}}}":
                missing_fields.append(field)
        
        if missing_fields:
            self.logger.warning(f"Missing or unresolved configuration fields: {missing_fields}")
            self.logger.warning("Some features may not work properly without these values")
        else:
            self.logger.info("Basic configuration validation passed")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a configuration value."""
        self.config[key] = value
    
    def save_config(self):
        """Save the current configuration to file."""
        try:
            # Create a copy without resolved environment variables for saving
            save_config = {}
            for key, value in self.config.items():
                # Skip saving sensitive fields that should come from environment
                if key in ['instagram_app_secret', 'instagram_access_token', 'openai_api_key', 
                          'json2video_api_key', 'gcs_api_key_path']:
                    continue
                save_config[key] = value
            
            with open(self.config_path, 'w') as f:
                json.dump(save_config, f, indent=4)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def get_instagram_config(self) -> Dict[str, Any]:
        """Get Instagram-specific configuration."""
        return {
            'app_id': self.get('instagram_app_id'),
            'app_secret': self.get('instagram_app_secret'),
            'user_id': self.get('instagram_user_id'),
            'access_token': self.get('instagram_access_token'),
            'token_expiration': self.get('instagram_token_expiration'),
            'days_before_refresh': self.get('instagram_days_before_refresh', 7)
        }
    
    def get_gcs_config(self) -> Dict[str, Any]:
        """Get GCS-specific configuration."""
        return {
            'bucket': self.get('gcs_bucket'),
            'api_key_path': self.get('gcs_api_key_path'),
            'folders': self.get('gcs_folders', []),
            'draft_folder': self.get('gcs_draft_folder', 'draft_videos')
        }
    
    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI-specific configuration."""
        return {
            'api_key': self.get('openai_api_key'),
            'assistant_id': self.get('gpt_assistant_id'),
            'thread_id': self.get('gpt_thread_id'),
            'creation_prompt': self.get('gpt_creation_prompt')
        }
    
    def get_json2video_config(self) -> Dict[str, Any]:
        """Get JSON2Video-specific configuration."""
        return {
            'api_key': self.get('json2video_api_key'),
            'base_url': self.get('json2video_base_url', 'https://api.json2video.com/v2'),
            'timeout': self.get('json2video_timeout', 300)
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging-specific configuration."""
        return {
            'log_level': self.get('log_level', 'INFO'),
            'log_file': self.get('log_file'),
            'log_max_size': self.get('log_max_size', '10MB'),
            'log_backup_count': self.get('log_backup_count', 5),
            'log_console_output': self.get('log_console_output', True)
        }
    
    def update_instagram_tokens(self, access_token: str, expiration: str):
        """Update Instagram access token and expiration."""
        self.config['instagram_access_token'] = access_token
        self.config['instagram_token_expiration'] = expiration
        self.logger.info("Instagram tokens updated")
    
    def is_instagram_token_expired(self) -> bool:
        """Check if Instagram token is expired or expiring soon."""
        try:
            expiration_str = self.config.get('instagram_token_expiration')
            if not expiration_str:
                return True
            
            expiration_date = datetime.strptime(expiration_str, "%Y-%m-%d %H:%M:%S")
            days_left = (expiration_date - datetime.now()).days
            days_before_refresh = self.config.get('instagram_days_before_refresh', 7)
            
            self.logger.debug(f"Instagram token expires in {days_left} days")
            return days_left <= days_before_refresh
            
        except Exception as e:
            self.logger.error(f"Error checking Instagram token expiration: {e}")
            return True  # Assume expired if there's an error
    
    def get_days_until_token_refresh(self) -> int:
        """Get the number of days until the Instagram token needs refresh."""
        try:
            expiration_str = self.config.get('instagram_token_expiration')
            if not expiration_str:
                return 0
            
            expiration_date = datetime.strptime(expiration_str, "%Y-%m-%d %H:%M:%S")
            days_left = (expiration_date - datetime.now()).days
            return max(0, days_left)
            
        except Exception as e:
            self.logger.error(f"Error calculating days until token refresh: {e}")
            return 0

# Convenience function for getting configuration
def get_config(config_path: str = "autopost_config.json") -> ConfigManager:
    """Get a configuration manager instance."""
    return ConfigManager(config_path)
