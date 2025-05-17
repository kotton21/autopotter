import requests
import os
import json
import argparse
import time
from datetime import datetime

class InstagramConfig:
    def __init__(self, config_path="config_fb.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            #TODO  user for app_id, app_secret, user_id, and short_access_token
            self.config = {
                "APP_ID": "your app_id",
                "APP_SECRET": "your app_secret",
                "USER_ID": "your_user_id",
                "ACCESS_TOKEN": "your_new_long_lived_token",
                "TOKEN_EXPIRATION": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.save_config()
            print("No config file found....  Creating new one.")
            print("self.config_path:", self.config_path)
            print("Please populate it and re-execute.")
            exit()
    
    def save_config(self):
        with open(self.config_path, "w+") as f:
            json.dump(self.config, f, indent=4)
    
    def is_token_expired(self):
        if not self.config["TOKEN_EXPIRATION"]:
            return True
        expiration_date = datetime.strptime(self.config["TOKEN_EXPIRATION"], "%Y-%m-%d %H:%M:%S")
        return (expiration_date - datetime.now()).days <= 2
    
    def refresh_access_token(self):
        print("Refreshing access token...")
        self.get_long_lived_token()
    
    def get_long_lived_token(self):
        url = f"https://graph.facebook.com/v22.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.config.get("APP_ID"),
            "client_secret": self.config.get("APP_SECRET"),
            "fb_exchange_token": self.config["ACCESS_TOKEN"]
        }
        response = requests.get(url, params=params)
        response_data = response.json()
        
        if "access_token" in response_data and "expires_in" in response_data:
            self.config["ACCESS_TOKEN"] = response_data["access_token"]
            expiration_timestamp = int(time.time()) + response_data["expires_in"]
            self.config["TOKEN_EXPIRATION"] = datetime.fromtimestamp(expiration_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Expiration datetime: {self.config['TOKEN_EXPIRATION']}")
            self.save_config()
            print("Config file updated successfully.")
        else:
            print("Failed to obtain long-lived token:", response_data)

class InstagramVideoUploader:
    def __init__(self, config_path="config_fb.json", log_file=None):
        self.log_file = log_file
        self.IGconfig = InstagramConfig(config_path=config_path)
        if self.IGconfig.is_token_expired():
            self.IGconfig.refresh_access_token()

    def create_media_container(self, caption="Test Caption"):
        url = f"https://graph.facebook.com/v22.0/{self.IGconfig.config['USER_ID']}/media"
        payload = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": self.IGconfig.config["ACCESS_TOKEN"]
        }
        response = requests.post(url, data=payload)
        response_data = response.json()
        return response_data.get("id"), response_data.get("uri")

    def upload_video(self, creation_id, video_path):
        file_size = os.path.getsize(video_path)
        url = f"https://rupload.facebook.com/ig-api-upload/v22.0/{creation_id}"
        headers = {
            "Authorization": f"OAuth {self.IGconfig.config['ACCESS_TOKEN']}",
            "offset": "0",
            "file_size": str(file_size)
        }
        
        with open(video_path, "rb") as video_file:
            response = requests.post(url, headers=headers, data=video_file)
        
        return response.json()

    def publish_video(self, creation_id):
        url = f"https://graph.facebook.com/v22.0/{self.IGconfig.config['USER_ID']}/media_publish"
        payload = {
            "creation_id": creation_id,
            "access_token": self.IGconfig.config["ACCESS_TOKEN"]
        }
        response = requests.post(url, data=payload)
        return response.json()

    def upload_and_publish(self, video_path, caption):
        self.log_message("Creating media container...")
        creation_id, _ = self.create_media_container(caption)
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
            print(msg)
        else:
            with open(self.log_file, "a") as f:
                f.write(msg)

if __name__ == "__main__":
    #  Generate a new access token here:
    #  https://developers.facebook.com/tools/explorer

    description = (
        "Upload and publish a video to Instagram.\n"
        "Generate a new access token here:\n"
        "https://developers.facebook.com/tools/explorer"
    )
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("video_path", type=str, help="Path to the video file")
    parser.add_argument("caption", type=str, help="Caption for the video")
    
    parser.print_help()
    args = parser.parse_args()
    
    uploader = InstagramVideoUploader()
    uploader.upload_and_publish(args.video_path, args.caption)


