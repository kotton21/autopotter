import requests
import json
import time
import os
from datetime import datetime
from pathlib import Path
import tempfile

import sys
from pathlib import Path

# Add the parent directory to Python path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager

# Try importing logger from autopotter_tools first, fallback to local import
try:
    from autopotter_tools.simplelogger import Logger
except ImportError:
    from simplelogger import Logger


class Json2VideoAPI:
    """
    Minimal client for the json2video API
    Only implements the methods required by autopotter_workflow.py
    """
    
    def __init__(self, config_path="autopost_config.enhanced.json"):
        self.config_manager = ConfigManager(config_path)
        
        # Initialize API settings from config
        self.api_key = self.config_manager.config["json2video_api_key"]
        self.base_url = self.config_manager.config["json2video_base_url"]
        self.timeout = self.config_manager.config["json2video_timeout"]
        
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        # Validate API key
        if not self.api_key or self.api_key.startswith("${"):
            error_msg = "Please set your json2video API key in the config file"
            Logger.error(error_msg)
            raise ValueError(error_msg)
        
        Logger.info(f"Json2VideoAPI initialized with base URL: {self.base_url}")
        
    def test_connection(self):
        """Test the connection to the json2video API"""
        try:
            Logger.info("Testing connection to json2video API...")
            
            url = f"{self.base_url}/movies"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                Logger.info("API connection successful")
                return True
            elif response.status_code == 401:
                Logger.error("API key authentication failed")
                return False
            elif response.status_code == 403:
                Logger.error("API access forbidden - check API key permissions")
                return False
            else:
                Logger.warning(f"Unexpected response: {response.status_code}")
                return False
                
        except Exception as e:
            Logger.error(f"Connection test failed: {e}")
            return False
    
    def create_video(self, video_config):
        """Create a video using json2video API"""
        try:
            url = f"{self.base_url}/movies"
            Logger.info("Creating video with API...")
            
            response = requests.post(url, headers=self.headers, json=video_config)
            response.raise_for_status()
            
            result = response.json()
            project_id = result.get('project')
            
            if not project_id:
                error_msg = "No project ID in API response"
                Logger.error(error_msg)
                raise Exception(error_msg)
            
            Logger.info(f"Video creation initiated. Project ID: {project_id}")
            
            # Return with 'id' field for compatibility
            result['id'] = project_id
            return result
            
        except Exception as e:
            Logger.error(f"Error creating video: {e}")
            raise
    
    def wait_for_completion(self, project_id):
        """Wait for video creation to complete"""
        start_time = time.time()
        Logger.info(f"Waiting for project {project_id} to complete...")
        
        # Note: We don't validate project existence upfront because newly created projects
        # might not immediately appear in the API response. We'll check during the first status check.
        
        while time.time() - start_time < self.timeout:
            try:
                status_info = self.get_project_status(project_id)
                
                # Extract status from response
                if 'movie' in status_info:
                    movie_info = status_info['movie']
                    status = movie_info.get('status', 'unknown')
                    success = movie_info.get('success', False)
                else:
                    status = status_info.get('status', 'unknown')
                    success = status_info.get('success', False)
                
                if status == 'done' or success:
                    Logger.info(f"Project {project_id} completed successfully!")
                    
                    # Log the finished video URL
                    if 'movie' in status_info:
                        movie_info = status_info['movie']
                        video_url = movie_info.get('url')
                        if video_url:
                            Logger.info(f"Finished video URL: {video_url}")
                        else:
                            Logger.warning("No video URL found in response")
                    else:
                        video_url = status_info.get('url')
                        if video_url:
                            Logger.info(f"Finished video URL: {video_url}")
                        else:
                            Logger.warning("No video URL found in response")
                    
                    return status_info
                elif status == 'error':
                    # Get more details about the error if available
                    error_msg = "Video creation failed"
                    if 'movie' in status_info:
                        movie_info = status_info['movie']
                        if 'error' in movie_info:
                            error_msg = f"Video creation failed: {movie_info['error']}"
                        elif 'message' in movie_info:
                            error_msg = f"Video creation failed: {movie_info['message']}"
                    Logger.error(error_msg)
                    raise Exception(error_msg)
                elif status in ['pending', 'processing', 'running']:
                    Logger.debug(f"Still {status}... waiting 10 seconds")
                    time.sleep(10)
                elif status == 'not_found_yet':
                    Logger.debug(f"Project {project_id} not found yet (may be newly created), waiting 10 seconds")
                    time.sleep(10)
                else:
                    Logger.warning(f"Unknown status: {status}, waiting 10 seconds")
                    time.sleep(10)
                    
            except Exception as e:
                Logger.error(f"Error checking status: {e}")
                # If we get an error during status check, it likely means the project failed
                # Don't continue waiting, raise the exception to stop the process
                raise Exception(f"Video creation failed with error: {e}")
        
        error_msg = f"Video creation timed out after {self.timeout} seconds"
        Logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_project_status(self, project_id):
        """Get the current status of a video creation project"""
        try:
            url = f"{self.base_url}/movies"
            params = {"project": project_id}
            
            Logger.debug(f"Getting project status for {project_id}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            # Look for the specific project in the response
            if 'movies' in result and isinstance(result['movies'], list):
                for movie in result['movies']:
                    if movie.get('project') == project_id:
                        return movie
            
            # If we can't find the specific project, return the full response
            return result
            
        except Exception as e:
            Logger.error(f"Error getting project status: {e}")
            raise
    
    def download_video(self, project_id, output_path=None):
        """Download the completed video"""
        try:
            # Get project info first
            status_info = self.get_project_status(project_id)
            
            # Extract download URL
            if 'movie' in status_info:
                movie_info = status_info['movie']
                download_url = movie_info.get('url')
            else:
                download_url = status_info.get('url')
            
            if not download_url:
                error_msg = "No download URL found in project status"
                Logger.error(error_msg)
                raise Exception(error_msg)
            
            # Determine output path
            if not output_path:
                filename = f"json2video_{project_id}.mp4"
                output_path = os.path.join(tempfile.gettempdir(), filename)
            
            # Download the video
            Logger.info(f"Downloading video to: {output_path}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            Logger.info(f"Video downloaded successfully to: {output_path}")
            return output_path
            
        except Exception as e:
            Logger.error(f"Error downloading video: {e}")
            raise


def main():
    """Simple test function"""
    try:
        api = Json2VideoAPI()
        if api.test_connection():
            Logger.info("Connection test passed")
        else:
            Logger.error("Connection test failed")
    except Exception as e:
        Logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()
