import requests
import os
import json
import argparse
import time
from datetime import datetime
import sys
from pathlib import Path

# Add the parent directory to Python path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager


class InstagramVideoUploader:
    def __init__(self, config_path="autopost_config.enhanced.json", log_file=None):
        self.log_file = log_file
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_instagram_config()
        
        # Check if token needs refresh
        if self.config_manager.is_instagram_token_expired():
            self.log_message("Instagram token is expired or expiring soon. Please refresh it.")
            self.log_message("You can use the config.py methods to refresh your token.")

    def create_media_container(self, caption="Test Caption", audio_id=None):
        url = f"https://graph.facebook.com/v22.0/{self.config['user_id']}/media"
        payload = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": self.config["access_token"]
        }
        if audio_id:
            payload["audio_id"] = audio_id  # Add the audio_id if provided
            self.log_message(f"Adding Audio. ID: {audio_id}")

        response = requests.post(url, data=payload)
        response_data = response.json()

        if "id" in response_data and "uri" in response_data:
            self.log_message(f"Media container created successfully. ID: {response_data['id']}")
        else:
            self.log_message(f"Failed to create media container: {response_data}")

        return response_data.get("id"), response_data.get("uri")

    def upload_video(self, creation_id, video_path):
        file_size = os.path.getsize(video_path)
        url = f"https://rupload.facebook.com/ig-api-upload/v22.0/{creation_id}"
        headers = {
            "Authorization": f"OAuth {self.config['access_token']}",
            "offset": "0",
            "file_size": str(file_size)
        }
        
        with open(video_path, "rb") as video_file:
            response = requests.post(url, headers=headers, data=video_file)
        
        return response.json()

    def publish_video(self, creation_id):
        url = f"https://graph.facebook.com/v22.0/{self.config['user_id']}/media_publish"
        payload = {
            "creation_id": creation_id,
            "access_token": self.config["access_token"]
        }
        response = requests.post(url, data=payload)
        return response.json()

    def upload_and_publish(self, video_path, caption):
        self.log_message("Creating media container...")
        creation_id, _ = self.create_media_container(caption)
        if not creation_id:
            self.log_message("Media container is None. Exiting...")
            self.log_message("Token may be expired: https://developers.facebook.com/tools/explorer")
            return
        self.log_message(f"Media container created: {creation_id}")
        
        self.log_message("Uploading video...")
        upload_result = self.upload_video(creation_id, video_path)
        self.log_message(f"Upload result: {upload_result}")
        
        self.log_message("Publishing video...")
        publish_result = self.publish_video(creation_id)
        self.log_message(f"Publish result: {publish_result}")
        
        self.log_message("Video uploaded successfully!")

    def log_message(self, message):
        """Log a message to the log file with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] InstagramUploader: {message}\n"
        if self.log_file is None:
            print(msg, end="")
        else:
            with open(self.log_file, "a") as f:
                f.write(msg)


def main():
    """Simple test function"""
    try:
        uploader = InstagramVideoUploader()
        print("✅ Instagram uploader initialized successfully")
        print("✅ Configuration loaded from centralized config")
        
        # Show token status
        days_until_refresh = uploader.config_manager.get_days_until_token_refresh()
        print(f"📅 Instagram token expires in {days_until_refresh} days")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()