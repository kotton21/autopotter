#!/usr/bin/env python3
"""
Integration test for Instagram upload/delete via Graph API.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from autopotter_tools.instagram_api import InstagramVideoUploader
from autopotter_tools.simplelogger import Logger


def main():
    tests_dir = Path(__file__).parent
    video_path = tests_dir / "anothertest2.mov"
    if not video_path.exists():
        Logger.error(f"Test video not found: {video_path}")
        return 1

    config_path = Path(__file__).parent.parent / "autopost_config.enhanced.json"
    uploader = InstagramVideoUploader(config_path=str(config_path))
    caption = "Autopotter integration test - please ignore"

    Logger.info("Starting Instagram upload test...")
    media_id, _ = uploader.upload_and_publish(str(video_path), caption)
    if not media_id or not media_id == None:
        Logger.error(f"Upload failed: {media_id}")
        return 1

    Logger.info(f"Upload succeeded. Media ID: {media_id}")
    Logger.info("Deleting uploaded media...")

    delete_result = uploader.delete_instagram_post(media_id)
    if not delete_result.get("success"):
        Logger.error(f"Delete failed: {delete_result}")
        return 1

    Logger.info("Integration test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

