import os
import json
import argparse
import sys
from datetime import datetime
from autopotter_tools.gptassistant_api import GPTAssistant
from autopotter_tools.instagram_api import InstagramVideoUploader
from moviepy.video.io.VideoFileClip import VideoFileClip

# Default config file path
DEFAULT_CONFIG_PATH = os.path.expanduser("~/printer_data/config/autopost_config.json")

def load_or_create_config(config_path):
    """Load the config file or create a default one if it doesn't exist."""
    if not os.path.exists(config_path):
        default_config = {
            "video_folder": os.path.expanduser("~/printer_data/timelapse"),
            "uploaded_videos": [],
            "log_file": os.path.expanduser("~/printer_data/logs/autopotter.log"),
            "caption_prompt": "Write a new instagram reel caption. The new caption should be totally different from previous prompts you've provided, but align with your personality."
        }
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    with open(config_path, "r") as f:
        return json.load(f)

def log_message(log_file, message):
    """Log a message to the log file with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

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


def main():
    parser = argparse.ArgumentParser(description="Automatically post videos to Instagram.")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH, help="Path to the config file.")
    args = parser.parse_args()

    # Load or create config
    config = load_or_create_config(args.config)
    video_folder = config["video_folder"]
    uploaded_videos = config["uploaded_videos"]
    log_file = config["log_file"]
    caption_prompt = config["caption_prompt"]

    log_message(log_file, "Starting autopost script.")

    # Find a new video to upload
    uploaded_video_files = [item["video"] for item in uploaded_videos]
    video_path = find_new_video(video_folder, uploaded_video_files)
    if not video_path:
        log_message(log_file, "No new videos found to upload.")
        sys.exit(0)  # No error, just no work to do

    log_message(log_file, f"Found new video to upload: {video_path}")

    # Generate a caption using GPT
    try:
        gpt_assistant = GPTAssistant()
        caption = gpt_assistant.prompt(caption_prompt)
        # caption = generate_caption(caption_prompt)
        log_message(log_file, f"Generated caption: {caption}")
    except Exception as e:
        log_message(log_file, f"Error generating caption: {e}")
        sys.exit(2)  # Exit with error code 2 for caption generation failure

    # Upload the video to Instagram
    try:
        ig_uploader = InstagramVideoUploader()
        ig_uploader.upload_and_publish(video_path, caption)
        # upload_and_publish(video_path, caption)
        log_message(log_file, f"Successfully uploaded video: {video_path}")
        # Save both the video filename and caption into the config
        uploaded_videos.append({"video": os.path.basename(video_path), "caption": caption})
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
        
if __name__ == "__main__":
    main()