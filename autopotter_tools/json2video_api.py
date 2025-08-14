import requests
import json
import time
import os
from datetime import datetime
from pathlib import Path
import tempfile


class Json2VideoConfig:
    """
    Configuration management for Json2Video API
    Follows the same pattern as InstagramConfig in instagram_api.py
    """
    
    def __init__(self, config_path="config_json2video.json", log_file=None):
        self.log_file = log_file
        self.config_path = config_path
        self.config = self.load_config()
    
    def log_message(self, message):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] Json2VideoConfig: {message}\n"
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(msg)
        else:
            print(msg, end="")
    
    def load_config(self):
        """Load the config file or create a default one if it doesn't exist."""
        try:
            self.log_message(f"Loading configuration from {self.config_path}...")
            with open(self.config_path, "r") as f:
                config = json.load(f)
                self.log_message("Configuration loaded successfully.")
                
                # Resolve environment variables
                config = self.resolve_environment_variables(config)
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            self.log_message("No valid config file found. Creating a new one...")
            self.config = {
                "API_KEY": "your_api_key_here",
                "BASE_URL": "https://api.json2video.com/v2",
                "DEFAULT_TIMEOUT": 300,
                "DEFAULT_POLL_INTERVAL": 10,
                "DEFAULT_RESOLUTION": "full-hd",
                "DEFAULT_VIDEO_VOLUME": 0.5,
                "DEFAULT_AUDIO_VOLUME": 0.2,
                "DEFAULT_VOICEOVER_VOLUME": 0.8,
                "DEFAULT_VOICE": "en-US-JennyMultilingualNeural",
                "AUTO_CLEANUP": True,
                "LOG_LEVEL": "INFO"
            }
            self.save_config()
            self.log_message(f"New config file created at {self.config_path}. Please edit it to set your API key and preferences.")
            exit(1)

    def resolve_environment_variables(self, config):
        """Replace ${ENV_VAR} placeholders with actual environment variable values"""
        resolved_config = {}
        
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]  # Remove ${ and }
                env_value = os.getenv(env_var)
                if env_value:
                    resolved_config[key] = env_value
                    self.log_message(f"Resolved {key} from environment variable {env_var}")
                else:
                    raise ValueError(f"Environment variable {env_var} not set for {key}")
            else:
                resolved_config[key] = value
        
        return resolved_config
    
    def save_config(self):
        """Save the current configuration to file."""
        self.log_message(f"Saving configuration to {self.config_path}...")
        
        # Only create directory if there's a directory component in the path
        config_dir = os.path.dirname(self.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=4)
        self.log_message("Configuration saved successfully.")
    
    def get_defaults(self):
        """Get the default values for template variables"""
        return self.config.get("defaults", {})
    
    def get_video_config(self):
        """Get the complete video configuration from basic config with defaults"""
        basic_config = self.get_basic_config()
        defaults = self.get_defaults()
        # Return the basic_config with defaults applied
        return basic_config
    
    def get_basic_config(self):
        """Get the basic configuration template with wildcards"""
        return self.config.get("basic_config", {})
    
    def get_output_path(self):
        """Get the default output path"""
        return "./edited_video_demo.mp4"
    
    def get_timeout(self):
        """Get the default timeout"""
        return self.config.get("DEFAULT_TIMEOUT", 300)
    
    def validate_basic_config(self):
        """Validate that basic configuration has required structure"""
        basic_config = self.get_basic_config()
        
        if not basic_config:
            raise ValueError("No basic_config section found in configuration")
        
        if "scenes" not in basic_config:
            raise ValueError("basic_config missing 'scenes' section")
        
        if not basic_config["scenes"]:
            raise ValueError("basic_config has no scenes")
        
        for i, scene in enumerate(basic_config["scenes"]):
            if "elements" not in scene:
                raise ValueError(f"Scene {i} missing 'elements' section")
            if not scene["elements"]:
                raise ValueError(f"Scene {i} has no elements")
        
        self.log_message("Basic configuration validation passed")
        return True


class Json2VideoAPI:
    """
    Comprehensive client for the json2video API
    Documentation: https://api.json2video.com/v2/docs
    """
    
    def __init__(self, config_path="config_json2video.json", log_file=None):
        self.log_file = log_file
        self.config_manager = Json2VideoConfig(config_path=config_path, log_file=log_file)
        self.config = self.config_manager.config
        
        # Initialize API settings from config
        self.api_key = self.config["API_KEY"]
        self.base_url = self.config["BASE_URL"]
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        # Validate API key
        if self.api_key == "your_api_key_here":
            self.log_message("❌ ERROR: Please set your actual API key in the config file")
            self.log_message(f"Edit {self.config_path} and set API_KEY to your real json2video API key")
            exit(1)
        
        self.log_message("Json2VideoAPI initialized successfully")
        
    def log_message(self, message):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] Json2VideoAPI: {message}\n"
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(msg)
        else:
            print(msg, end="")
    
    def create_video(self, video_config):
        """
        Create a video using json2video API
        
        Args:
            video_config (dict): Video configuration including scenes, elements, etc.
            
        Returns:
            dict: API response with project ID and status
        """
        try:
            url = f"{self.base_url}/movies"
            self.log_message(f"Creating video with config: {json.dumps(video_config, indent=2)}")
            self.log_message(f"API URL: {url}")
            self.log_message(f"Headers: {json.dumps(self.headers, indent=2)}")
            
            response = requests.post(url, headers=self.headers, json=video_config)
            self.log_message(f"Response status code: {response.status_code}")
            self.log_message(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            result = response.json()
            self.log_message(f"API Response: {json.dumps(result, indent=2)}")
            
            # Check if we got a valid project ID (json2video v2 uses 'project' instead of 'id')
            project_id = result.get('project')
            if not project_id:
                self.log_message(f"❌ ERROR: No project ID in API response")
                self.log_message(f"Response status: {response.status_code}")
                self.log_message(f"Response headers: {dict(response.headers)}")
                self.log_message(f"Full response: {result}")
                
                # Check for error messages in the response
                if 'error' in result:
                    raise Exception(f"API Error: {result['error']}")
                elif 'message' in result:
                    raise Exception(f"API Message: {result['message']}")
                else:
                    raise Exception("No project ID returned from API. Check the response above for details.")
            
            self.log_message(f"Video creation initiated successfully. Project ID: {project_id}")
            
            # Return the result with an 'id' field for compatibility
            result['id'] = project_id
            return result
            
        except requests.exceptions.RequestException as e:
            self.log_message(f"Error creating video: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.log_message(f"Response status: {e.response.status_code}")
                self.log_message(f"Response text: {e.response.text}")
            raise
        except Exception as e:
            self.log_message(f"Unexpected error in create_video: {e}")
            raise
    
    def get_project_status(self, project_id):
        """
        Get the current status of a video creation project
        
        Args:
            project_id (str): The project ID returned from create_video
            
        Returns:
            dict: Current status and metadata
        """
        try:
            # Based on the API response, it seems like we need to use a different endpoint
            # Let's try the movies endpoint with the project ID as a query parameter
            url = f"{self.base_url}/movies"
            params = {"project": project_id}
            
            self.log_message(f"Getting status for project {project_id}")
            self.log_message(f"Status URL: {url} with params: {params}")
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            self.log_message(f"Status response: {json.dumps(result, indent=2)}")
            
            # Look for the specific project in the response
            if 'movies' in result and isinstance(result['movies'], list):
                for movie in result['movies']:
                    if movie.get('project') == project_id:
                        return movie
            
            # If we can't find the specific project, return the full response
            return result
            
        except requests.exceptions.RequestException as e:
            self.log_message(f"Error getting project status: {e}")
            raise
    
    def wait_for_completion(self, project_id, timeout=None, poll_interval=None):
        """
        Wait for video creation to complete
        
        Args:
            project_id (str): The project ID to monitor
            timeout (int): Maximum time to wait in seconds (uses config default if None)
            poll_interval (int): Time between status checks in seconds (uses config default if None)
            
        Returns:
            dict: Final status when complete
        """
        # Use config defaults if not specified
        timeout = timeout or self.config["DEFAULT_TIMEOUT"]
        poll_interval = poll_interval or self.config["DEFAULT_POLL_INTERVAL"]
        
        start_time = time.time()
        self.log_message(f"Waiting for project {project_id} to complete...")
        
        while time.time() - start_time < timeout:
            status_info = self.get_project_status(project_id)
            self.log_message(f"Status info: {json.dumps(status_info, indent=2)}")
            
            # Extract the actual status from the nested structure
            if 'movie' in status_info:
                movie_info = status_info['movie']
                status = movie_info.get('status', 'unknown')
                success = movie_info.get('success', False)
                message = movie_info.get('message', 'No message')
            else:
                status = status_info.get('status', 'unknown')
                success = status_info.get('success', False)
                message = status_info.get('message', 'No message')
            
            self.log_message(f"Current status: {status}, success: {success}, message: {message}")
            
            if status == 'done' or success:
                self.log_message(f"Project {project_id} completed successfully!")
                return status_info
            elif status == 'error' or (not success and 'error' in message.lower()):
                error_msg = message if message else 'Unknown error'
                raise Exception(f"Video creation failed: {error_msg}")
            elif status in ['pending', 'processing', 'running']:
                self.log_message(f"Still {status}... waiting {poll_interval} seconds")
                time.sleep(poll_interval)
            else:
                self.log_message(f"Unknown status: {status}, waiting {poll_interval} seconds")
                time.sleep(poll_interval)
        
        raise Exception(f"Video creation timed out after {timeout} seconds")
    
    def download_video(self, project_id, output_path=None):
        """
        Download the completed video
        
        Args:
            project_id (str): The project ID of the completed video
            output_path (str): Path to save the video (optional)
            
        Returns:
            str: Path to the downloaded video file
        """
        try:
            # Get project info first
            status_info = self.get_project_status(project_id)
            self.log_message(f"Download status info: {json.dumps(status_info, indent=2)}")
            
            # Extract the movie info from the nested structure
            if 'movie' in status_info:
                movie_info = status_info['movie']
                status = movie_info.get('status', 'unknown')
                success = movie_info.get('success', False)
                download_url = movie_info.get('url')
            else:
                status = status_info.get('status', 'unknown')
                success = status_info.get('success', False)
                download_url = status_info.get('url')
            
            self.log_message(f"Download check - status: {status}, success: {success}, url: {download_url}")
            
            if status != 'done' or not success:
                raise Exception(f"Video not ready for download. Status: {status}, Success: {success}")
            
            if not download_url:
                raise Exception("No download URL found in project status")
            
            # Determine output path
            if not output_path:
                filename = f"json2video_{project_id}.mp4"
                output_path = os.path.join(tempfile.gettempdir(), filename)
            
            # Download the video
            self.log_message(f"Downloading video to: {output_path}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.log_message(f"Video downloaded successfully to: {output_path}")
            return output_path
            
        except Exception as e:
            self.log_message(f"Error downloading video: {e}")
            raise
    
    def create_video_and_wait(self, video_config, timeout=None):
        """
        Create video and wait for completion, returning the web URL
        
        Args:
            video_config (dict): Video configuration
            timeout (int): Maximum time to wait for completion (uses config default if None)
            
        Returns:
            str: Web URL location of the rendered video file
        """
        try:
            # Step 1: Create the video
            creation_result = self.create_video(video_config)
            project_id = creation_result.get('id')
            
            if not project_id:
                raise Exception("No project ID returned from video creation")
            
            # Step 2: Wait for completion
            self.wait_for_completion(project_id, timeout=timeout)
            
            # Step 3: Get the video URL (don't download)
            # Since wait_for_completion already validated the project completed successfully,
            # we can just get the final status to extract the URL
            status_info = self.get_project_status(project_id)
            video_url = status_info.get('url') or status_info.get('movie', {}).get('url')
            
            if video_url:
                return video_url
            else:
                raise Exception("No download URL found in project status")
            
        except Exception as e:
            self.log_message(f"Error in create_video_and_wait workflow: {e}")
            raise

    def test_connection(self):
        """
        Test the connection to the json2video API
        """
        try:
            self.log_message("Testing connection to json2video API...")
            
            # Try to get the API status or test endpoint
            test_url = f"{self.base_url}/movies"
            self.log_message(f"Testing URL: {test_url}")
            self.log_message(f"Using API key: {self.api_key[:8]}...{self.api_key[-4:]}")
            
            # Make a simple GET request to test connectivity
            response = requests.get(test_url, headers=self.headers)
            self.log_message(f"Test response status: {response.status_code}")
            
            if response.status_code == 200:
                self.log_message("✅ API connection successful")
                # Log the response to see what we get
                try:
                    response_data = response.json()
                    self.log_message(f"Test response: {json.dumps(response_data, indent=2)}")
                except:
                    self.log_message(f"Test response text: {response.text}")
                return True
            elif response.status_code == 401:
                self.log_message("❌ API key authentication failed")
                return False
            elif response.status_code == 403:
                self.log_message("❌ API access forbidden - check API key permissions")
                return False
            else:
                self.log_message(f"⚠️ Unexpected response: {response.status_code}")
                self.log_message(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_message(f"❌ Connection test failed: {e}")
            return False
    
    def render_video_from_template(self, video_source_url, audio_source_url, voiceover_text):
        """
        Render a video using the basic_config template with provided variables
        
        Args:
            video_source_url (str): URL to the source video file
            audio_source_url (str): URL to the source audio file
            voiceover_text (str): Text for the voiceover
            
        Returns:
            str: Web URL location of the rendered video file
        """
        try:
            # Get the basic config template
            basic_config = self.config_manager.get_basic_config()
            
            if not basic_config:
                raise ValueError("No basic_config section found in configuration")
            
            # Create a copy of the config and replace template variables
            video_config = basic_config.copy()
            
            # Replace template variables in the config
            for scene in video_config.get('scenes', []):
                for element in scene.get('elements', []):
                    if element.get('type') == 'video':
                        element['src'] = video_source_url
                    elif element.get('type') == 'audio':
                        element['src'] = audio_source_url
                    elif element.get('type') == 'voice':
                        element['text'] = voiceover_text
            
            self.log_message(f"Rendering video with template variables:")
            self.log_message(f"  Video: {video_source_url}")
            self.log_message(f"  Audio: {audio_source_url}")
            self.log_message(f"  Voiceover: {voiceover_text}")
            self.log_message(f"  Voice: en-US-JennyMultilingualNeural (hardcoded)")
            self.log_message(f"  Resolution: instagram-story (hardcoded)")
            
            # Create the video and wait for completion
            video_url = self.create_video_and_wait(video_config)
            
            self.log_message(f"✅ Video successfully rendered at: {video_url}")
            return video_url
            
        except Exception as e:
            self.log_message(f"❌ Error rendering video from template: {e}")
            raise
    
    def render_video_and_download(self, video_source_url, audio_source_url, voiceover_text, output_path=None):
        """
        Render a video using the basic_config template and download it locally
        
        Args:
            video_source_url (str): URL to the source video file
            audio_source_url (str): URL to the source audio file
            voiceover_text (str): Text for the voiceover
            output_path (str): Path to save the video (optional, uses config default if None)
            
        Returns:
            str: Path to the downloaded video file
        """
        try:
            # Step 1: Render the video using the template
            video_url = self.render_video_from_template(
                video_source_url=video_source_url,
                audio_source_url=audio_source_url,
                voiceover_text=voiceover_text
            )
            
            self.log_message(f"Video rendered successfully at: {video_url}")
            
            # Step 2: Download the video locally
            if not output_path:
                output_path = self.config_manager.get_output_path()
            
            self.log_message(f"Downloading video to: {output_path}")
            
            # Download the video from the URL
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.log_message(f"✅ Video successfully downloaded to: {output_path}")
            return output_path
            
        except Exception as e:
            self.log_message(f"❌ Error in render_video_and_download workflow: {e}")
            raise





def main():
    """
    Test json2video API functionality using basic_config with command-line parameters
    """
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test json2video API with basic_config template')
    parser.add_argument('--video', '-v', help='Video source URL')
    parser.add_argument('--audio', '-a', help='Audio source URL')
    parser.add_argument('--text', '-t', help='Voiceover text')

    
    args = parser.parse_args()
    
    try:
        print("=== Json2Video API Test ===")
        print("Using basic_config template with command-line parameters...")
        print()
        
        # Initialize API client
        api_client = Json2VideoAPI()
        
        # Validate basic configuration
        try:
            api_client.config_manager.validate_basic_config()
            print("✅ Basic configuration validation passed")
        except ValueError as e:
            print(f"❌ Basic configuration error: {e}")
            return 1
        
        # Get defaults and apply command-line overrides
        defaults = api_client.config_manager.get_defaults()
        video_url = args.video or defaults.get('video_source_url')
        audio_url = args.audio or defaults.get('audio_source_url')
        voiceover_text = args.text or defaults.get('voiceover_text')
        
        print("Configuration:")
        print(f"  Video: {video_url}")
        print(f"  Audio: {audio_url}")
        print(f"  Voiceover: {voiceover_text}")
        print(f"  Voice: en-US-JennyMultilingualNeural (hardcoded)")
        print(f"  Resolution: instagram-story (hardcoded)")
        print()
        
        # Test API connection
        print("Testing API connection...")
        if not api_client.test_connection():
            print("❌ API connection failed. Please check your API key and internet connection.")
            return 1
        print("✅ API connection successful!")
        print()
        
        # Create video using the template
        print("Starting video creation with template...")
        video_url = api_client.render_video_from_template(
            video_source_url=video_url,
            audio_source_url=audio_url,
            voiceover_text=voiceover_text
        )
        
        print(f"\n✅ SUCCESS! Video rendered at: {video_url}")
        
        # Download the video for demo purposes
        print("Downloading video for demo...")
        try:
            output_path = api_client.config_manager.get_output_path()
            # Download the video from the URL
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Video successfully downloaded to: {output_path}")
        except Exception as e:
            print(f"⚠️  Download failed: {e}")
            print(f"Video is still available at: {video_url}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
