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


class Json2VideoAPI:
    """
    Minimal client for the json2video API
    Only implements the methods required by autopotter_workflow.py
    """
    
    def __init__(self, config_path="autopost_config.enhanced.json"):
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_json2video_config()
        
        # Initialize API settings from config
        self.api_key = self.config["api_key"]
        self.base_url = self.config["base_url"]
        self.timeout = self.config["timeout"]
        
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        # Validate API key
        if not self.api_key or self.api_key.startswith("${"):
            raise ValueError("Please set your json2video API key in the config file")
        
        print(f"Json2VideoAPI initialized with base URL: {self.base_url}")
        
    def test_connection(self):
        """Test the connection to the json2video API"""
        try:
            print("Testing connection to json2video API...")
            
            url = f"{self.base_url}/movies"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                print("✅ API connection successful")
                return True
            elif response.status_code == 401:
                print("❌ API key authentication failed")
                return False
            elif response.status_code == 403:
                print("❌ API access forbidden - check API key permissions")
                return False
            else:
                print(f"⚠️ Unexpected response: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def create_video(self, video_config):
        """Create a video using json2video API"""
        try:
            url = f"{self.base_url}/movies"
            print(f"Creating video with API...")
            
            response = requests.post(url, headers=self.headers, json=video_config)
            response.raise_for_status()
            
            result = response.json()
            project_id = result.get('project')
            
            if not project_id:
                raise Exception("No project ID in API response")
            
            print(f"✅ Video creation initiated. Project ID: {project_id}")
            
            # Return with 'id' field for compatibility
            result['id'] = project_id
            return result
            
        except Exception as e:
            print(f"❌ Error creating video: {e}")
            raise
    
    def wait_for_completion(self, project_id):
        """Wait for video creation to complete"""
        start_time = time.time()
        print(f"Waiting for project {project_id} to complete...")
        
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
                    print(f"✅ Project {project_id} completed successfully!")
                    
                    # Print the finished video URL
                    if 'movie' in status_info:
                        movie_info = status_info['movie']
                        video_url = movie_info.get('url')
                        if video_url:
                            print(f"🎬 Finished video URL: {video_url}")
                        else:
                            print("⚠️ No video URL found in response")
                    else:
                        video_url = status_info.get('url')
                        if video_url:
                            print(f"🎬 Finished video URL: {video_url}")
                        else:
                            print("⚠️ No video URL found in response")
                    
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
                    raise Exception(error_msg)
                elif status in ['pending', 'processing', 'running']:
                    print(f"Still {status}... waiting 10 seconds")
                    time.sleep(10)
                elif status == 'not_found_yet':
                    print(f"Project {project_id} not found yet (may be newly created), waiting 10 seconds")
                    time.sleep(10)
                else:
                    print(f"Unknown status: {status}, waiting 10 seconds")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"❌ Error checking status: {e}")
                # If we get an error during status check, it likely means the project failed
                # Don't continue waiting, raise the exception to stop the process
                raise Exception(f"Video creation failed with error: {e}")
        
        raise Exception(f"Video creation timed out after {self.timeout} seconds")
    
    def get_project_status(self, project_id):
        """Get the current status of a video creation project"""
        try:
            url = f"{self.base_url}/movies"
            params = {"project": project_id}
            
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
            print(f"❌ Error getting project status: {e}")
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
                raise Exception("No download URL found in project status")
            
            # Determine output path
            if not output_path:
                filename = f"json2video_{project_id}.mp4"
                output_path = os.path.join(tempfile.gettempdir(), filename)
            
            # Download the video
            print(f"Downloading video to: {output_path}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Video downloaded successfully to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Error downloading video: {e}")
            raise


def main():
    """Simple test function"""
    try:
        api = Json2VideoAPI()
        if api.test_connection():
            print("✅ Connection test passed")
        else:
            print("❌ Connection test failed")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
