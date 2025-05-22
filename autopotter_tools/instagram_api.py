import requests
import os
import json
import argparse
import time
from datetime import datetime

class InstagramConfig:
    def __init__(self, config_path="config_fb.json", log_file=None):
        self.log_file = log_file
        self.config_path = config_path
        self.config = self.load_config()
        self.log_message("InstagramConfig initialized successfully.")

    def load_config(self):
        try:
            self.log_message(f"Loading configuration from {self.config_path}...")
            with open(self.config_path, "r") as f:
                config = json.load(f)
                self.log_message("Configuration loaded successfully.")
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            self.log_message("No valid config file found. Creating a new one...")
            self.config = {
                "APP_ID": "your app_id",
                "APP_SECRET": "your app_secret",
                "USER_ID": "your_user_id",
                "ACCESS_TOKEN": "your_new_long_lived_token",
                "TOKEN_EXPIRATION": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.save_config()
            self.log_message(f"New config file created at {self.config_path}. Please populate it and re-execute.")
            exit()

    def save_config(self):
        self.log_message(f"Saving configuration to {self.config_path}...")
        with open(self.config_path, "w+") as f:
            json.dump(self.config, f, indent=4)
        self.log_message("Configuration saved successfully.")

    def is_token_expired(self):
        if not self.config["TOKEN_EXPIRATION"]:
            self.log_message("Token expiration date is missing. Assuming token is expired.")
            return True
        expiration_date = datetime.strptime(self.config["TOKEN_EXPIRATION"], "%Y-%m-%d %H:%M:%S")
        days_left = (expiration_date - datetime.now()).days
        self.log_message(f"Token expires in {days_left} days.")
        return days_left <= 2

    def refresh_access_token(self):
        self.log_message("Refreshing access token...")
        self.get_long_lived_token()

    def get_long_lived_token(self):
        self.log_message("Requesting a long-lived access token...")
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
            self.log_message(f"New access token obtained. Token expires on {self.config['TOKEN_EXPIRATION']}.")
            self.save_config()
            self.log_message("Config file updated successfully with the new token.")
        else:
            self.log_message(f"Failed to obtain long-lived token: {response_data}")

    def log_message(self, message):
        """Log a message to the log file with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] InstagramConfig: {message}\n"
        if self.log_file is None:
            print(msg)
        else:
            with open(self.log_file, "a") as f:
                f.write(msg)



class InstagramVideoUploader:
    def __init__(self, config_path="config_fb.json", log_file=None):
        self.log_file = log_file
        self.IGconfig = InstagramConfig(config_path=config_path, log_file=log_file)
        if self.IGconfig.is_token_expired():
            self.IGconfig.refresh_access_token()

    def search_music(self, query):
        """Search for music tracks based on a query (e.g., genre or playlist)."""
        url = "https://graph.facebook.com/v22.0/search"
        params = {
            "type": "music",
            "q": query,
            "access_token": self.IGconfig.config["ACCESS_TOKEN"]
        }
        response = requests.get(url, params=params)
        response_data = response.json()

        if "data" in response_data:
            self.log_message(f"Music search results: {response_data['data']}")
            return response_data["data"]
        else:
            self.log_message(f"Failed to search for music: {response_data}")
            return []
        

    def recommend_music(self):
        """Get music recommendations from the Facebook API."""
        url = "https://graph.facebook.com/v22.0/audio/recommendations"
        params = {
            "type": "FACEBOOK_FOR_YOU", #"FACEBOOK_NEW_MUSIC",#"FACEBOOK_POPULAR_MUSIC",
            "access_token": self.IGconfig.config["ACCESS_TOKEN"]
        }
        response = requests.get(url, params=params)
        response_data = response.json()

        if "data" in response_data:
            self.log_message(f"Music recommendations: {response_data['data']}")
            return response_data["data"]
        else:
            self.log_message(f"Failed to get music recommendations: {response_data}")
            return []
    

    def create_media_container(self, caption="Test Caption", audio_id=None):
        url = f"https://graph.facebook.com/v22.0/{self.IGconfig.config['USER_ID']}/media"
        payload = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": self.IGconfig.config["ACCESS_TOKEN"]
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
            print(msg)
        else:
            with open(self.log_file, "a") as f:
                f.write(msg)

if __name__ == "__main__":
    # Generate a new access token here:
    # https://developers.facebook.com/tools/explorer

    description = (
        "Instagram Video Uploader Tool.\n"
        "Actions:\n"
        "  upload_and_publish: Upload and publish a video to Instagram.\n"
        "  search_music: Search for music tracks based on a query.\n"
        "  rec_music: Get music recommendations from the Facebook API.\n"
        "Generate a new access token here:\n"
        "https://developers.facebook.com/tools/explorer"
    )
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "action",
        type=str,
        choices=["upload_and_publish", "search_music", "rec_music"],
        help="Action to perform: 'upload_and_publish', 'search_music', or 'rec_music'"
    )
    parser.add_argument(
        "--video_path",
        type=str,
        help="Path to the video file (required for upload_and_publish)"
    )
    parser.add_argument(
        "--caption",
        type=str,
        help="Caption for the video (required for upload_and_publish)"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Text to search for music (required for search_music)"
    )

    args = parser.parse_args()

    uploader = InstagramVideoUploader()

    if args.action == "upload_and_publish":
        if not args.video_path or not args.caption:
            print("Error: --video_path and --caption are required for upload_and_publish.")
            exit(1)
        uploader.upload_and_publish(args.video_path, args.caption)

    elif args.action == "search_music":
        if not args.query:
            print("Error: --query is required for search_music.")
            exit(1)
        results = uploader.search_music(args.query)
        print("Music Search Results:")
        for track in results:
            print(f"ID: {track['id']}, Title: {track['title']}, Artist: {track['artist']}")

    elif args.action == "rec_music":
        results = uploader.recommend_music()
        print("Music Recommendations:")
        for track in results:
            print(f"ID: {track['id']}, Title: {track['title']}, Artist: {track['artist']}")