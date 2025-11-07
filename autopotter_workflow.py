#!/usr/bin/env python3
"""
Minimal script that orchestrates the entire workflow:
1. Calls enhanced_autodraft with predefined config, outfile, and prompt
2. Uploads the first parsed_json2video_configs to json2video
3. Uses instagram_api to upload that video to Instagram using the caption from autodraft
"""

import json
import os
import sys
import argparse
from pathlib import Path

from autopotter_tools.logger import get_logger

from enhanced_autodraft import main_autodraft
from autopotter_tools.json2video_manager import Json2VideoAPI
from autopotter_tools.instagram_api import InstagramVideoUploader
from autopotter_tools.instagram_analytics import InstagramAnalyticsManager


def run_autopotter_workflow(config_file, outfile, prompt_override, video_outfile, video_draft_only):
    """Run the complete autopotter workflow"""
    
    print("🚀 Starting Autopotter Workflow...")
    print(f"📁 Config: {config_file}")
    print(f"📁 Output: {outfile}")
    print(f"📝 Prompt: {prompt_override}")
    print(f"🎬 Video Output: {video_outfile}")
    print(f"📱 Instagram Upload: {'Disabled' if video_draft_only else 'Enabled'}")
    print()
    
    try:
        # Load config to check for analytics reload option
        from config import ConfigManager
        config = ConfigManager(config_file)
        

        ####### STEP 0.5: Reload Instagram analytics if configured #######
        if config.get('autopost_reload_ig_analytics', False):
            print("\n📊 Step 1.5: Reloading Instagram analytics...")
            try:
                analytics_manager = InstagramAnalyticsManager(config_file)
                analytics_output = config.get('gpt_responses_other_files_to_include', None)['ig_analytics']
                analytics_manager.export_to_json(analytics_output)
                print(f"✅ Instagram analytics reloaded and saved to: {analytics_output}")
            except Exception as e:
                print(f"⚠️  Warning: Failed to reload Instagram analytics: {e}")
                print("Continuing with existing analytics data...")
        else:
            print("\n⏭️  Skipping Instagram analytics reload (autopost_reload_ig_analytics = false)")
        

        ####### STEP 1: Run enhanced_autodraft #######
        print("\n📝 Step 1: Running enhanced_autodraft...")
        main_autodraft(outfile, config_file, prompt_override)
        
        # Load the autodraft output
        with open(outfile, 'r') as f:
            autodraft_data = json.load(f)
  
        # Extract video configs and count available options
        parsed_output = autodraft_data.get('parsed_output')
        parsed_json2video_configs = autodraft_data.get('parsed_json2video_configs')
        
        if not parsed_output or not parsed_output.get('videos'):
            raise Exception("No videos found in parsed_output")
        
        if not parsed_json2video_configs:
            raise Exception("No json2video configs found in parsed_json2video_configs")
        
        # Count available videos and randomly select one
        available_videos = parsed_output['videos']
        available_configs = parsed_json2video_configs
        
        print(f"🎲 Found {len(available_videos)} video ideas to choose from")
        
        # Step 2: Upload to json2video
        print("\n🎬 Step 2: Uploading to json2video...")
        json2video_api = Json2VideoAPI(config_file)
        
        # Test connection first
        if not json2video_api.test_connection():
            raise Exception("Failed to connect to json2video API")
        
        
        # Try videos until one succeeds
        import random
        video_success = False
        while available_videos and not video_success:
            # Randomly select one video and its corresponding config
            selected_index = random.randint(0, len(available_videos) - 1)
            selected_video = available_videos[selected_index]
            selected_json2vid_config = available_configs[selected_index]
            
            # Check if config was successfully parsed
            if not selected_json2vid_config or selected_json2vid_config == {}:
                print(f"⚠️  Video #{selected_index + 1} has invalid config, trying another...")
                available_videos.pop(selected_index)
                available_configs.pop(selected_index)
                continue
            
            selected_caption = selected_video['video_caption']
            print(f"🎯 Trying video #{selected_index + 1} of {len(available_videos)}")
            print(f"📝 Caption: {selected_video['video_caption'][:100]}...")
            print(f"📹 Video config has {len(selected_json2vid_config.get('scenes', []))} scenes")
            
            try:
                # Create video and wait for completion
                print("Create video with json2video...")
                creation_result = json2video_api.create_video(selected_json2vid_config)
                project_id = creation_result['id']
                
                # Wait for completion
                print("Wait for video to complete...")
                completion_status = json2video_api.wait_for_completion(project_id)
                
                # Extract video metadata from completion status
                movie_info = completion_status['movie']
                video_duration = movie_info.get('duration')
                print(f"⏱️  Duration: {movie_info.get('duration')} seconds")
                print(f"📐 Dimensions: {movie_info.get('width')}x{movie_info.get('height')}")
                print(f"💾 File size: {movie_info.get('size')}")
                print(f"🔗 Video URL: {movie_info.get('url')}")

                if video_duration < 2:
                    raise Exception("❌ Video duration is less than 2 seconds")
                
                # Download the video to the specified output file
                print(f"\nDownloading video to: {video_outfile}")
                video_path = json2video_api.download_video(project_id, video_outfile)
                print(f"✅ Video downloaded to: {video_path}")
                
                video_success = True
                
            except Exception as e:
                print(f"⚠️  Video #{selected_index + 1} failed: {e}")
                print(f"🔄 Trying another video...")
                available_videos.pop(selected_index)
                available_configs.pop(selected_index)
                continue
        
        if not video_success:
            raise Exception("❌ All videos failed to render successfully")

        
        
        # If video-draft-only is specified, stop here
        if video_draft_only:
            print("\n🎬 Video draft completed successfully!")
            print(f"📁 Video saved to: {video_outfile}")
            print("⏭️  Skipping Instagram upload (video-draft-only mode)")
            return True
        
        # Step 3: Upload to Instagram
        print("\n📱 Step 3: Uploading to Instagram...")
        instagram_uploader = InstagramVideoUploader(config_file)
        thumbnail_offset = (video_duration-1)*1000
        print(f"Uploading video with caption: {selected_caption[:100]}...")
        instagram_uploader.upload_and_publish(video_path, selected_caption, thumbnail_offset)
        print("✅ Video uploaded to Instagram successfully!")
        
        # Cleanup temporary file after Instagram upload
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"🧹 Cleaned up temporary file: {video_path}")
        
        print("\n🎉 Autopotter workflow completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        return False


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Autopotter workflow: autodraft → json2video → Instagram')
    parser.add_argument('--config', '-c', 
                       default='autopost_config.enhanced.json',
                       help='Config file path (default: autopost_config.enhanced.json)')
    parser.add_argument('--draft-outfile', '-o',
                       default='resources/autodraft_output.enhanced.json',
                       help='Output file path (default: autodraft_output.enhanced.json)')
    parser.add_argument('--prompt', '-p',
                       default=None,
                       help='Prompt for GPT (default: Output 5 different and varied complete ideas for Autopotter social media post.)')
    parser.add_argument('--video-outfile', '--vo',
                       default='autopotter_video_draft.mp4',
                       help='Video output file path (default: autopotter_video_draft.mp4)')
    parser.add_argument('--video-draft-only', '-v',
                       action='store_true', default=False,
                       help='Include to create a video and download, do not upload to Instagram (default: False)')
    
    args = parser.parse_args()
    
    success = run_autopotter_workflow(args.config, args.draft_outfile, args.prompt, args.video_outfile, args.video_draft_only)
    sys.exit(0 if success else 1)
