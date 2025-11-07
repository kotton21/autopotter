import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from autopotter_tools.logger import get_logger

class ConfigManager:
    """
    Simple configuration management for the enhanced video generation system.
    Provides flat key-value structure with environment variable resolution.
    """
    
    def __init__(self, config_path: str = "autopost_config.enhanced.json"):
        self.config_path = config_path
        self.temp_config_path = config_path.replace('.json', '.temp.json')
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
            
            # Load temporary config parameters if temp file exists
            if os.path.exists(self.temp_config_path):
                try:
                    with open(self.temp_config_path, 'r') as f:
                        temp_config = json.load(f)
                    
                    # Merge temp config into main config (temp values override main values)
                    self.config.update(temp_config)
                    self.logger.info(f"Loaded {len(temp_config)} temporary configuration parameters from {self.temp_config_path}")
                    
                except Exception as e:
                    self.logger.warning(f"Could not load temporary config from {self.temp_config_path}: {e}")
            
            # First, load environment variables from .env file
            self.load_dotenv(self.config.get('env_file_path', '.env'))
            
            # Resolve environment variables
            self.config = self.resolve_environment_variables(self.config)
            
            self.logger.info("Configuration loaded successfully")
            return self.config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default."""
        
        if key == 'instagram_access_token':
            if self.is_instagram_token_expired():
                self.logger.info("Instagram token is expired or expiring soon. Attempting automatic refresh...")
                self.refresh_instagram_token()
        
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a configuration value and save to temporary config file."""
        try:
            # Update in-memory configuration
            self.config[key] = value
            
            # Load existing temp config if it exists
            temp_config = {}
            if os.path.exists(self.temp_config_path):
                try:
                    with open(self.temp_config_path, 'r') as f:
                        temp_config = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Could not read existing temp config file: {e}")
            
            # Update temp config with new value
            temp_config[key] = value
            
            # Save to temporary config file
            with open(self.temp_config_path, 'w') as f:
                json.dump(temp_config, f, indent=4)
            
            self.logger.info(f"Configuration value '{key}' set and saved to temporary config: {self.temp_config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to set configuration value '{key}': {e}")
            raise
    
    def load_dotenv(self, env_file_path: str = ".env") -> bool:
        """
        Load environment variables from a .env file.
        
        Args:
            env_file_path: Path to the .env file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(env_file_path):
                self.logger.warning(f"Environment file {env_file_path} not found")
                return False
            
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
                            self.logger.debug(f"Loaded environment variable: {key}")
                        else:
                            self.logger.debug(f"Environment variable {key} already set, skipping")
            
            self.logger.info(f"Environment variables loaded from {env_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load environment variables from {env_file_path}: {e}")
            return False
    
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
            "instagram_days_before_token_should_autorefresh": 7,
            
            # Instagram Analytics Configuration
            "max_media_items": 7,
            "max_comments_per_media": 10,
            "max_replies_per_comment": 5,
            
            # GCS Configuration
            "gcs_bucket": "autopot1-printdump",
            "gcs_api_key_path": "your_gcs_api_key_path",
            "gcs_folders": ["video_uploads", "music_uploads", "completed_works", "wip_photos", "build_photos"],
            "gcs_draft_folder": "draft_videos",
            
            # OpenAI Configuration
            "openai_api_key": "${OPENAI_API_KEY}",
            "gpt_assistant_id": None,
            "gpt_thread_id": None,
            "gpt_creation_prompt": "You are a creative AI assistant for 3D printing pottery content.",
            "always_create_new_thread": True,
            
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
            
            # Environment Configuration
            "env_file_path": ".env",
            
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
    
    
    
    def _update_env_file(self, key: str, value: str) -> bool:
        """Update a key-value pair in the .env file."""
        env_file_path = self.config.get('env_file_path', '.env')
        
        try:
            if not os.path.exists(env_file_path):
                # Create .env file if it doesn't exist
                with open(env_file_path, 'w') as f:
                    f.write(f"{key}={value}\n")
                self.logger.info(f"Created new .env file at {env_file_path}")
                return True
            
            # Read existing .env file
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
            
            # Update or add the key-value pair
            key_found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    key_found = True
                    break
            
            if not key_found:
                lines.append(f"{key}={value}\n")
            
            # Write back to .env file
            with open(env_file_path, 'w') as f:
                f.writelines(lines)
            
            self.logger.debug(f"Updated {key} in .env file {env_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update .env file {env_file_path}: {e}")
            return False
    
    def _update_environment_variable(self, key: str, value: str) -> bool:
        """Update an environment variable in the current process."""
        try:
            os.environ[key] = value
            self.logger.debug(f"Updated environment variable {key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update environment variable {key}: {e}")
            return False
    
    
    def update_instagram_tokens(self, access_token: str, expiration: str):
        """Update Instagram access token and expiration with full persistence."""
        # Update in-memory configuration
        self.config['instagram_access_token'] = access_token
        
        # Update environment variable for current process
        self._update_environment_variable('INSTAGRAM_ACCESS_TOKEN', access_token)
        
        # Update .env file for persistence across restarts
        self._update_env_file('INSTAGRAM_ACCESS_TOKEN', access_token)
        
        self.logger.info("Instagram tokens updated and persisted to environment and .env file")
    
    def refresh_instagram_token(self):
        """Automatically refresh the Instagram access token using Facebook API."""
        try:
            self.logger.info("Requesting a new long-lived access token from Facebook...")
            
            import requests
            
            url = "https://graph.facebook.com/v22.0/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.get('instagram_app_id'),
                "client_secret": self.get('instagram_app_secret'),
                "fb_exchange_token": self.get('instagram_access_token')
            }
            
            response = requests.get(url, params=params)
            response_data = response.json()
            
            if "access_token" in response_data:
                new_token = response_data["access_token"]
                self.logger.info("✅ New access token obtained successfully")
                
                # Get new expiration date from Facebook API
                new_expiration = self._get_facebook_token_expiration(new_token)
                
                # Update access token in environment and .env file only
                self._update_environment_variable('INSTAGRAM_ACCESS_TOKEN', new_token)
                self._update_env_file('INSTAGRAM_ACCESS_TOKEN', new_token)
                
                # Update token expiration in main config (but don't save access token)
                self.set('instagram_token_expiration', new_expiration)
                
                # Reset access token back to placeholder before saving
                # self.config['instagram_access_token'] = '${INSTAGRAM_ACCESS_TOKEN}'
                
                # # Save the updated config (access token will be placeholder, expiration will be updated)
                # self.save_config()
                
                self.logger.info("✅ Instagram token refreshed and updated successfully")
                
            else:
                self.logger.error(f"❌ Failed to obtain new token: {response_data}")
                raise Exception("Unable to refresh Instagram access token")
                
        except Exception as e:
            self.logger.error(f"❌ Error refreshing Instagram access token: {e}")
            raise
    
    def _get_facebook_token_expiration(self, access_token: str) -> str:
        """Get token expiration by polling Facebook API."""
        try:
            self.logger.info("Getting token expiration date from Facebook API...")
            
            import requests
            
            url = "https://graph.facebook.com/debug_token"
            params = {
                "input_token": access_token,
                "access_token": self.get('instagram_app_id') + "|" + self.get('instagram_app_secret')
            }
            
            response = requests.get(url, params=params)
            response_data = response.json()
            
            if "data" in response_data and "expires_at" in response_data["data"]:
                exp = response_data["data"]["expires_at"]
                if exp == 0:
                    if "data_access_expires_at" in response_data["data"]:
                        exp = response_data["data"]["data_access_expires_at"]
                    else:
                        raise Exception("No valid expiration date found")
                
                expiration_date = datetime.fromtimestamp(exp)
                new_expiration = expiration_date.strftime('%Y-%m-%d %H:%M:%S')
                
                self.logger.info(f"✅ Token expiration determined: {new_expiration}")
                return new_expiration
                
            else:
                self.logger.warning("⚠️ Could not determine new token expiration, using current time + 60 days")
                # Fallback: set expiration to 60 days from now
                fallback_expiration = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
                return fallback_expiration
                
        except Exception as e:
            self.logger.error(f"⚠️ Error getting token expiration: {e}")
            # Fallback: set expiration to 60 days from now
            fallback_expiration = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
            return fallback_expiration
    
    def is_instagram_token_expired(self) -> bool:
        """Check if Instagram token is expired or expiring soon using Facebook API."""
        try:
            access_token = self.config['instagram_access_token']
            if not access_token or access_token.startswith('${'):
                self.logger.warning("No valid Instagram access token available")
                return True
            
            # Get fresh expiration data from Facebook API
            fresh_expiration = self._get_facebook_token_expiration(access_token)
            expiration_date = datetime.strptime(fresh_expiration, "%Y-%m-%d %H:%M:%S")
            days_left = (expiration_date - datetime.now()).days
            days_before_refresh = self.config.get('instagram_days_before_token_should_autorefresh', 7)
            
            self.logger.debug(f"Instagram token expires in {days_left} days (from Facebook API)")
            return days_left <= days_before_refresh
            
        except Exception as e:
            self.logger.error(f"Error checking Instagram token expiration from Facebook API: {e}")
            return True  # Assume expired if there's an error
    

# Convenience function for getting configuration
def get_config(config_path: str = "autopost_config.enhanced.json") -> ConfigManager:
    """Get a configuration manager instance."""
    return ConfigManager(config_path)


if __name__ == "__main__":
    config = get_config()
    print(json.dumps(config.config, indent=2))

