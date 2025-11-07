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

# Try importing logger from autopotter_tools first, fallback to local import
try:
    from autopotter_tools.simplelogger import Logger
except ImportError:
    from simplelogger import Logger


class InstagramVideoUploader:
    def __init__(self, config_path="autopost_config.enhanced.json", log_file=None):
        # self.log_file = log_file
        self.config_manager = ConfigManager(config_path)
        # self.config = self.config_manager.get_instagram_config()

        self.access_token = self.config_manager.get('instagram_access_token', None)
        self.user_id = self.config_manager.get('instagram_user_id', None)

        # Validate required configuration
        if not self.access_token:
            raise ValueError("Instagram access token not configured")
        if not self.user_id:
            raise ValueError("Instagram user ID not configured")
        
        # Check if token needs refresh
        # if self.config_manager.is_instagram_token_expired():
        #     self.log_message("Instagram token is expired or expiring soon. Please refresh it.")
        #     self.log_message("You can use the config.py methods to refresh your token.")

    def create_media_container(self, caption="Test Caption", audio_id=None, thumbnail_offset=None):
        url = f"https://graph.facebook.com/v22.0/{self.user_id}/media"
        payload = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": self.access_token
        }
        if thumbnail_offset:
            payload["thumb_offset"] = thumbnail_offset
            self.log_message(f"Adding Thumbnail Offset: {thumbnail_offset}")
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
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0",
            "file_size": str(file_size)
        }
        
        with open(video_path, "rb") as video_file:
            response = requests.post(url, headers=headers, data=video_file)
        
        return response.json()

    def publish_video(self, creation_id):
        url = f"https://graph.facebook.com/v22.0/{self.user_id}/media_publish"
        payload = {
            "creation_id": creation_id,
            "access_token": self.access_token
        }
        response = requests.post(url, data=payload)
        return response.json()

    def publish_from_url(self, video_url, video_caption):
        """
        Publish a reel directly from a video URL using Instagram Graph API.
        This method follows the Instagram API documentation for reels.
        
        Args:
            video_url (str): Public URL to the video file
            video_caption (str): Caption for the reel
            
        Returns:
            dict: API response with success status and details
        """
        try:
            self.log_message(f"🎬 Publishing reel from URL: {video_url}")
            self.log_message(f"📝 Caption: {video_caption}")
            
            # Step 1: Create reel container using video_url
            container_url = f"https://graph.facebook.com/v22.0/{self.user_id}/media"
            container_payload = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": video_caption,
                "access_token": self.access_token,
                # "thumb_offset": 5000
            }
            
            self.log_message("Creating reel container...")
            container_response = requests.post(container_url, data=container_payload)
            container_data = container_response.json()
            
            if "error" in container_data:
                error_msg = container_data["error"].get("message", "Unknown error")
                self.log_message(f"❌ Failed to create reel container: {error_msg}")
                return None
            
            if "id" not in container_data:
                self.log_message(f"❌ No container ID in response: {container_data}")
                return None
            
            container_id = container_data["id"]
            self.log_message(f"✅ Reel container created successfully. ID: {container_id}")

            # Step 1.5: Check if the container is ready
            self.log_message("Starting container readiness check...")
            container_ready = self.wait_for_container_ready(container_id)
            self.log_message(f"Container readiness result: {container_ready}")
            
            if container_ready == "ERROR":
                self.log_message("❌ Container ERROR")
                return None
            elif container_ready == "EXPIRED":
                self.log_message("❌ Container EXPIRED")
                return None
            elif container_ready == "FINISHED":
                self.log_message("✅ Container ready for publishing")
            else:
                self.log_message(f"⚠️ Container status: {container_ready}")
                return None
            
            # Step 2: Publish the container
            publish_url = f"https://graph.facebook.com/v22.0/{self.user_id}/media_publish"
            publish_payload = {
                "creation_id": container_id,
                "access_token": self.access_token
            }
            
            self.log_message("Publishing reel...")
            publish_response = requests.post(publish_url, data=publish_payload)
            publish_data = publish_response.json()
            
            if "error" in publish_data:
                error_msg = publish_data["error"].get("message", "Unknown error")
                self.log_message(f"❌ Failed to publish reel: {error_msg}")
                return None
            
            if "id" in publish_data:
                media_id = publish_data["id"]
                self.log_message(f"✅ Reel published successfully! Media ID: {media_id}")
                return True
            else:
                self.log_message(f"❌ No media ID in publish response: {publish_data}")
                return  None

        except requests.exceptions.RequestException as e:
            self.log_message(f"❌ Network error publishing reel: {e}")
            return None
        except Exception as e:
            self.log_message(f"❌ Unexpected error publishing reel: {e}")
            return None

    def wait_for_container_ready(self, container_id):
        """Wait for container to be ready, polling every 15s for max 20 iterations."""
        for i in range(20):
            self.log_message(f"Poll {i+1}/20 - container {container_id}")
            
            if i < 19:  # Don't sleep on last iteration
                time.sleep(15)

            try:
                response = requests.get(
                    f"https://graph.facebook.com/v22.0/{container_id}",
                    params={"fields": "status_code,status", "access_token": self.access_token}
                )
                status_code = response.json().get("status_code")
                status = response.json().get("status")
                self.log_message(f"Status_code: {status_code}, Status: {status}")
                
                if status_code in ["ERROR", "EXPIRED", "FINISHED", "PUBLISHED"]:
                    self.log_message(f"Final status: {status_code}")
                    return status_code
                    
            except Exception as e:
                self.log_message(f"Poll error: {e}")
        self.log_message("Timeout after 20 polls")
        return None

    def upload_and_publish(self, video_path, caption, thumbnail_offset=None):
        self.log_message("Creating media container...")
        creation_id, _ = self.create_media_container(caption, thumbnail_offset=thumbnail_offset)
        if not creation_id:
            self.log_message("Media container is None. Exiting...")
            self.log_message("Token may be expired: https://developers.facebook.com/tools/explorer")
            return None
        self.log_message(f"Media container created: {creation_id}")
        
        self.log_message("Uploading video...")
        upload_result = self.upload_video(creation_id, video_path)
        self.log_message(f"Upload result: {upload_result}")
        if upload_result.get("success") is False:
            self.log_message("Upload failed. Exiting...")
            return None
        
        self.log_message("Publishing video...")
        publish_result = self.publish_video(creation_id)
        self.log_message(f"Publish result: {publish_result}")
        if publish_result.get("success") is False:
            self.log_message("Publish failed. Exiting...")
            return None
        
        self.log_message("Video uploaded successfully!")

        return True




    def log_message(self, message):
        """Log a message using the simple logger."""
        # Determine log level based on message content
        if "❌" in message or "Failed" in message or "Error" in message or "error" in message.lower():
            Logger.error(message)
        elif "⚠️" in message or "Warning" in message or "warning" in message.lower():
            Logger.warning(message)
        else:
            Logger.info(message)


def main():
    """Test function with command line parameters"""
    parser = argparse.ArgumentParser(description='Instagram Video Uploader Test Tool')
    parser.add_argument('--video_file', '-v', type=str, default=None,
                       help='Path to video file for test upload')
    parser.add_argument('--video_url', '-u', type=str, default=None,
                       help='Public URL to video for publishing reel')
    parser.add_argument('--caption', '-c', type=str, default='Test video upload',
                       help='Caption for the video (default: Test video upload)')
    parser.add_argument('--config_file', '-f', type=str, default='autopost_config.enhanced.json',
                       help='Path to configuration file (default: autopost_config.enhanced.json)')
    
    args = parser.parse_args()
    
    try:
        print("=== Instagram Video Uploader Test ===")
        print(f"📁 Config file: {args.config_file}")
        
        # Initialize uploader
        uploader = InstagramVideoUploader(config_path=args.config_file)
        print("✅ Instagram uploader initialized successfully")
        print("✅ Configuration loaded from centralized config")
        
        # Show token status
        # days_until_refresh = uploader.config_manager.get_days_until_token_refresh()
        # print(f"📅 Instagram token expires in {days_until_refresh} days")
        
        # Test publish from URL if video URL is provided
        if args.video_url:
            print(f"\n🌐 Testing publish from URL: {args.video_url}")
            print(f"📝 Caption: {args.caption}")
            
            result = uploader.publish_from_url(args.video_url, args.caption)
            
            if result['success']:
                print("\n✅ Reel published successfully!")
                print(f"🆔 Container ID: {result.get('container_id')}")
                print(f"📱 Media ID: {result.get('media_id')}")
            else:
                print("\n❌ Reel publishing failed!")
                print(f"🚨 Error: {result.get('error')}")
                if 'container_response' in result:
                    print(f"📦 Container response: {result['container_response']}")
                if 'publish_response' in result:
                    print(f"📤 Publish response: {result['publish_response']}")
        
        # Test upload if video file is provided
        elif args.video_file:
            print(f"\n🎬 Uploading and publishing video: {args.video_file}")
            print(f"📝 Caption: {args.caption}")
            
            uploader.upload_and_publish(args.video_file, args.caption)
            
        else:
            print("\nℹ️ No video file or URL specified.")
            print("Use --video_file to test local file upload")
            print("Use --video_url to test publishing reel from URL")
            print("\nExamples:")
            print("  python instagram_api.py --video_file test.mp4 --caption 'Test video'")
            print("  python instagram_api.py --video_url https://example.com/video.mp4 --caption 'Test reel'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    main()