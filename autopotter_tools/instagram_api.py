import requests
import os
import json
import argparse
import time
from datetime import datetime

import json
import requests
from datetime import datetime, timedelta

class InstagramConfig:

    DAYS_LEFT_TO_REFRESH = 7  # Number of days before expiration to consider the token as expired

    def __init__(self, config_path="config_fb.json", log_file=None):
        self.log_file = log_file
        self.config_path = config_path
        self.config = self.load_config()

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
                "APP_ID": "your_app_id",
                "APP_SECRET": "your_app_secret",
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

    # def compute_access_token(self):
    #     """Compute the ACCESS_TOKEN dynamically using APP_ID and APP_SECRET."""
    #     if not self.config.get("APP_ID") or not self.config.get("APP_SECRET"):
    #         raise Exception("APP_ID or APP_SECRET is missing in the configuration.")
        
    #     access_token = f"{self.config.get("APP_ID")}|{self.config.get("APP_SECRET")}"
    #     return access_token

    def get_token_expiration(self):
        """Poll the Facebook API to get the token expiration date."""
        #self.log_message("Checking token expiration using the debug_token endpoint...")
        url = "https://graph.facebook.com/debug_token"
        params = {
            "input_token": self.config["ACCESS_TOKEN"],
            # "access_token": self.compute_access_token()  # Use app_id|app_secret for validation
            "access_token": self.config.get("APP_ID") + "|" + self.config.get("APP_SECRET")
        }
        response = requests.get(url, params=params)
        response_data = response.json()

        if "data" in response_data and (
            "expires_at" in response_data["data"] #or
            # "data_access_expires_at" in response_data["data"] #data_access_expires_at
        ):
            if "expires_at" in response_data["data"]:
                exp = response_data["data"]["expires_at"]
            # else:
            #     exp = response_data["data"]["data_access_expires_at"]
            
            expiration_timestamp = exp #response_data["data"]["data_access_expires_at"]
            expiration_date = datetime.fromtimestamp(expiration_timestamp)
            self.log_message(f"Debug_Token -> expires on {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}.")
            
            # Check if the expiration date is different from the one saved in the config
            current_expiration = self.config.get("TOKEN_EXPIRATION")
            new_expiration = expiration_date.strftime("%Y-%m-%d %H:%M:%S")
            if current_expiration != new_expiration:
                self.log_message(f"Updating token expiration date from {current_expiration} to {new_expiration}.")
                self.config["TOKEN_EXPIRATION"] = new_expiration
                self.save_config()
            
            return expiration_date
        else:
            # self.log_message(f"Failed to retrieve token expiration: {response_data}")
            raise Exception("Unable to retrieve token expiration from the Facebook API.")

    def is_token_expired(self):
        """Check if the token is expired or expiring soon."""
        try:
            expiration_date = self.get_token_expiration()
            days_left = (expiration_date - datetime.now()).days
            self.log_message(f"Token expires in {days_left} days.")
            return days_left <= InstagramConfig.DAYS_LEFT_TO_REFRESH
        except Exception as e:
            self.log_message(f"Error checking token expiration: {e}")
            return True  # Assume the token is expired if there's an error

    def check_refresh_access_token(self):
        """Refresh the access token if it is expired or expiring soon."""
        if self.is_token_expired():
            self.log_message("Token is expired or expiring soon. Refreshing access token...")
            self.get_long_lived_token()
        else:
            self.log_message("Token is valid and not expiring soon. No refresh needed.")

    def get_long_lived_token(self):
        """Request a new long-lived access token."""
        #self.log_message("Requesting a long-lived access token...")
        url = f"https://graph.facebook.com/v22.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.config.get("APP_ID"),
            "client_secret": self.config.get("APP_SECRET"),
            "fb_exchange_token": self.config["ACCESS_TOKEN"]
        }
        response = requests.get(url, params=params)
        response_data = response.json()

        if "access_token" in response_data:# and "expires_in" in response_data::
            self.config["ACCESS_TOKEN"] = response_data["access_token"]
            # expiration_timestamp = int(datetime.now().timestamp()) + response_data["expires_in"]
            #expiration_date = datetime.fromtimestamp(expiration_timestamp)
            #self.config["TOKEN_EXPIRATION"] = expiration_date.strftime("%Y-%m-%d %H:%M:%S")
            self.config["TOKEN_EXPIRATION"] = None
            self.log_message(f"New access token obtained. ")#Token expires on {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}.")
            self.save_config()
        else:
            self.log_message(f"Failed to obtain long-lived token: {response_data}")
            raise Exception("Unable to refresh access token.")

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
        #if self.IGconfig.is_token_expired():
        self.IGconfig.check_refresh_access_token()

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
        choices=["upload_and_publish", "search_music", "rec_music", "test_config"],
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
    parser.add_argument(
        "--config_path",
        type=str,
        default="config_fb.json",
        help="Path to the configuration file (default: config_fb.json)"
    )
    parser.add_argument(
        "--log_file",
        type=str,
        default=None,
        help="Path to the log file (default: None)"
    )


    args = parser.parse_args()

    

    if args.action == "upload_and_publish":
        if not args.config_path:
            print("Error: --config_path is required for upload_and_publish.")
            exit(1)
        uploader = InstagramVideoUploader(config_path=args.config_path)

        if not args.video_path or not args.caption:
            print("Error: --video_path and --caption are required for upload_and_publish.")
            exit(1)
        uploader.upload_and_publish(args.video_path, args.caption)

    elif args.action == "search_music":
        if not args.query:
            print("Error: --query is required for search_music.")
            exit(1)
        if not args.config_path:
            print("Error: --config_path is required for upload_and_publish.")
            exit(1)
        uploader = InstagramVideoUploader(config_path=args.config_path)

        results = uploader.search_music(args.query)
        print("Music Search Results:")
        for track in results:
            print(f"ID: {track['id']}, Title: {track['title']}, Artist: {track['artist']}")

    elif args.action == "rec_music":
        if not args.config_path:
            print("Error: --config_path is required for rec_music.")
            exit(1)
        uploader = InstagramVideoUploader(config_path=args.config_path)

        results = uploader.recommend_music()
        print("Music Recommendations:")
        for track in results:
            print(f"ID: {track['id']}, Title: {track['title']}, Artist: {track['artist']}")
    
    elif args.action == "test_config":
        print("main: running test_config")
        if not args.config_path:
            print("Error: --config_path is required for upload_and_publish.")
            exit(1)
        config = InstagramConfig(config_path=args.config_path, log_file=args.log_file)

        print("main: Checking if the access token is expired...")
        try:
            config.check_refresh_access_token()
            print("Access token checked.")
        except Exception as e:
            print(f"main: Failed to check access token: {e}")
        else:
            print("main: Access token is valid.")