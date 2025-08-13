import os
import json
import argparse
import sys
import requests
from datetime import datetime
from autopotter_tools.gptassistant_api import GPTAssistant
from autopotter_tools.instagram_api import InstagramVideoUploader
from autopotter_tools.googlestorage_api import GCSClient
from autopotter_tools.json2video_api import Json2VideoAPI
from moviepy.video.io.VideoFileClip import VideoFileClip
import re
import random


# Default config file path
DEFAULT_CONFIG_PATH = os.path.expanduser("./autopost_config.json")

def load_or_create_config(config_path):
    """Load the config file or create a default one if it doesn't exist."""
    if not os.path.exists(config_path):
        default_config = {
            "video_folder": os.path.expanduser("~/printer_data/timelapse"),
            "uploaded_videos": [],
            "log_file": os.path.expanduser("~/printer_data/logs/autopotter.log"),
            #"caption_prompt": "Write a new short instagram reel caption. The new caption should be totally different from previous prompts you've provided, but align with your personality.",
            "caption_prompt_list": [
                "Write a new short instagram reel caption. The new caption should be totally different from previous prompts you've provided, but align with your personality.",
                "You're about to upload a new video. Give a short caption that describes what you were thinking about when you created it. You were thinking about some aspect of your backstory.",
                "You're about to upload a new video. Give a short caption that comments on the current lack of civil right for robots",
                "You're about to upload a new video. Give a short caption that comments on human gender constructs from the perspective of a robot.",
                "You're about to upload a video of a new print which you think is absolutely stunning. Give a short caption that describes how you felt printing it.",
            ],
            "config_gpt_path": os.path.expanduser("~/printer_data/config/config_gpt.json"),
            "config_ig_path": os.path.expanduser("~/printer_data/config/config_fb.json"),
            "gcs_bucket": "autopot1-printdump",
            "gcs_api_key_path": os.path.expanduser("~/Downloads/autopot-cloud-6cb17ee04664.json"),
            "json2video_config_path": os.path.expanduser("./autopotter_tools/config_json2video.json"),
            "use_gcs_videos": True,
            "use_json2video": True,
            "audio_exclude_recent_count": 3,
        }
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        #return default_config
        print(f"Config file created at {config_path}. Please edit it to set your preferences.")
        exit(1)
    with open(config_path, "r") as f:
        return json.load(f)

def log_message(log_file, message):
    """Log a message to the log file with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] Autopost: {message}\n"
    if log_file is None:
        print(msg)
    else:
        with open(log_file, "a") as f:
            f.write(msg)

def find_new_video(video_folder, uploaded_videos, log_file=None):
    """Find the most recent video file that hasn't been uploaded yet and is at least 2 seconds long."""
    video_files = [f for f in os.listdir(video_folder) if f.endswith((".mp4", ".mov"))]
    video_files = sorted(video_files, key=lambda x: os.path.getmtime(os.path.join(video_folder, x)), reverse=True)
    for video in video_files:
        if video not in uploaded_videos:
            video_path = os.path.join(video_folder, video)
            try:
                with VideoFileClip(video_path) as clip:
                    if clip.duration >= 2:  # Check if the video is at least 2 seconds long
                        return video_path
            except Exception as e:
                if log_file:
                    log_message(log_file, f"Error processing video {video_path}: {e}")
                continue
    return None

def download_processed_video(video_url, local_path, log_file=None):
    """Download processed video from json2video URL"""
    try:
        log_message(log_file, f"Downloading processed video from: {video_url}")
        
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log_message(log_file, f"Successfully downloaded video to: {local_path}")
        return local_path
        
    except Exception as e:
        log_message(log_file, f"Error downloading processed video: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Automatically post videos to Instagram.")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH, help="Path to the config file.")
    args = parser.parse_args()

    # Load or create config
    config = load_or_create_config(args.config)
    video_folder = config["video_folder"]
    uploaded_videos = config["uploaded_videos"]
    log_file = config["log_file"]
    caption_prompt = config["caption_prompt_list"][random.randint(0, len(config["caption_prompt_list"]) - 1)]

    log_message(log_file, "Starting autopost script.")

    # Find a new video to upload
    video_path = None
    video_filename = None
    
    if config.get("use_gcs_videos", True):
        # Use GCS video discovery
        try:
            gcs_client = GCSClient(config["gcs_api_key_path"])
            selected_video = gcs_client.select_next_video(
                bucket_name=config["gcs_bucket"],
                uploaded_videos=uploaded_videos,
                log_file=log_file
            )
            
            if not selected_video:
                log_message(log_file, "No new videos found in GCS bucket.")
                sys.exit(0)
            
            video_gcs_url = selected_video['public_url']
            video_filename = selected_video['name']
            log_message(log_file, f"Found new video in GCS: {video_filename}")
            
        except Exception as e:
            log_message(log_file, f"GCS video discovery failed: {e}")
            log_message(log_file, "Falling back to local video discovery")
            config["use_gcs_videos"] = False
    
    if not config.get("use_gcs_videos", False):
        # Fall back to local video discovery (existing logic)
        uploaded_video_files = [item["video"] for item in uploaded_videos]
        video_path = find_new_video(video_folder, uploaded_video_files, log_file)
        if not video_path:
            log_message(log_file, "No new videos found to upload.")
            sys.exit(0)  # No error, just no work to do
        video_filename = os.path.basename(video_path)
        log_message(log_file, f"Found new local video to upload: {video_path}")

    # Generate a caption using GPT
    log_message(log_file, f"Generate caption")
    try:
        gpt_assistant = GPTAssistant(config_path=config["config_gpt_path"], log_file=log_file)
        caption = gpt_assistant.prompt(caption_prompt)
        # caption = "".join(caption)  # Join the list of strings into a single string
        caption = re.sub(r"[\u201c\u201d]", "", caption)
        # caption = generate_caption(caption_prompt)
        log_message(log_file, f"Generated caption: {caption}")
    except Exception as e:
        log_message(log_file, f"Error generating caption: {e}")
        sys.exit(2)  # Exit with error code 2 for caption generation failure

    # Process video through json2video if enabled
    if config.get("use_json2video", True) and config.get("use_gcs_videos", False):
        log_message(log_file, "Processing video through json2video API")
        try:
            # Get audio options and select one
            audio_options = gcs_client.get_audio_options(config["gcs_bucket"])
            if not audio_options:
                log_message(log_file, "Warning: No audio files found in GCS bucket")
                selected_audio = None
            else:
                selected_audio = gcs_client.select_random_audio(
                    audio_options, 
                    exclude_recent=config.get("audio_exclude_recent_count", 3)
                )
                if selected_audio:
                    audio_gcs_url = selected_audio['public_url']
                    log_message(log_file, f"Selected audio: {selected_audio['name']}")
                else:
                    log_message(log_file, "Warning: No audio selected")
                    audio_gcs_url = None
            
            # Process video through json2video
            json2video_client = Json2VideoAPI(config_path=config["json2video_config_path"], log_file=log_file)
            
            processed_video_url = json2video_client.render_video_from_template(
                video_source_url=video_gcs_url,
                audio_source_url=audio_gcs_url,
                voiceover_text=caption
            )
            
            # Download processed video
            temp_video_path = f"/tmp/processed_{os.path.basename(video_filename)}"
            local_processed_video = download_processed_video(
                processed_video_url, 
                temp_video_path,
                log_file
            )
            
            # Use processed video for Instagram upload
            video_path = local_processed_video
            log_message(log_file, f"Using processed video: {video_path}")
            
        except Exception as e:
            log_message(log_file, f"json2video processing failed: {e}")
            log_message(log_file, "Falling back to original video")
            # If json2video fails, we need to download the original video from GCS
            if config.get("use_gcs_videos", False):
                temp_video_path = f"/tmp/original_{os.path.basename(video_filename)}"
                local_original_video = download_processed_video(
                    video_gcs_url, 
                    temp_video_path,
                    log_file
                )
                video_path = local_original_video
            # If local video discovery, video_path is already set

    # Upload the video to Instagram
    log_message(log_file, f"Upload Video")
    try:
        ig_uploader = InstagramVideoUploader(config_path=config["config_ig_path"], log_file=log_file)
        ig_uploader.upload_and_publish(video_path, caption)
        # upload_and_publish(video_path, caption)
        log_message(log_file, f"Successfully uploaded video: {video_path}")
        # Save both the video filename and caption into the config
        uploaded_videos.append({"video": video_filename, "caption": caption})
    except Exception as e:
        log_message(log_file, f"Error uploading video: {e}")
        sys.exit(2)  # Exit with error code 2 for upload failure

    # Save the updated config
    try:
        with open(args.config, "w") as f:
            json.dump(config, f, indent=4)
        log_message(log_file, "Updated config file with uploaded video and caption.")
    except Exception as e:
        log_message(log_file, f"Error saving config file: {e}")
        sys.exit(1)  # Exit with error code 1 for config save failure
        
    # Cleanup temporary files
    if config.get("use_json2video", True) and video_path and video_path.startswith("/tmp/"):
        try:
            os.remove(video_path)
            log_message(log_file, f"Cleaned up temporary file: {video_path}")
        except Exception as e:
            log_message(log_file, f"Warning: Could not clean up temporary file {video_path}: {e}")
        
if __name__ == "__main__":
    main()