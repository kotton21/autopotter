#!/usr/bin/env python3
"""
Quick test script to load autodraft output and convert json2video_config_str to formatted JSON
"""

import json
import re
from pathlib import Path

# Try importing logger from autopotter_tools first, fallback to local import
try:
    from autopotter_tools.simplelogger import Logger
except ImportError:
    from simplelogger import Logger


# class JSON2VideoConfigParseError(Exception):
#     """Exception raised when json2video config parsing fails."""
#     pass


def parse_json2video_config(config_str, video_title="Unknown"):
    """
    Parse and validate a json2video config string with multiple fallback strategies.
    
    Args:
        config_str: The JSON string to parse
        video_title: Title of the video for error reporting
        
    Returns:
        dict: The successfully parsed JSON config
        
    """
    # Raises:
    #     JSON2VideoConfigParseError: If all parsing strategies fail

    Logger.debug(f"Parsing json2video config for video: {video_title}")
    
    if not config_str:
        error_msg = f"No config string provided for video '{video_title}'"
        Logger.error(error_msg)
        # raise JSON2VideoConfigParseError(error_msg)
        return {}
    
    Logger.debug(f"Config string length: {len(config_str)} characters")
    
    # Define repair strategies with their descriptions
    repair_strategies = [
        (lambda s: s, "direct parsing"),
        (lambda s: re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s), "control character removal"),
        (lambda s: s[s.find('{'):s.rfind('}')+1] if s.find('{') != -1 and s.rfind('}') > s.find('{') else s, "JSON extraction"),
        (lambda s: s.replace('\\"', '"').replace('\\n', '\n'), "escaped character fixing")
    ]
    
    # Try each repair strategy
    for repair_func, strategy_name in repair_strategies:
        try:
            Logger.debug(f"Trying parsing strategy: {strategy_name}")
            config_json = json.loads(repair_func(config_str))
            
            if strategy_name == "direct parsing":
                Logger.info(f"Successfully parsed json2video config for '{video_title}' (direct parsing)")
            else:
                Logger.info(f"Successfully parsed json2video config for '{video_title}' using {strategy_name}")
            
            return config_json
        except json.JSONDecodeError as e:
            Logger.debug(f"Strategy '{strategy_name}' failed: {str(e)}")
            continue
    
    # If all strategies fail, identify the specific issue
    # logger.warning(f"All parsing strategies failed for '{video_title}'")
    # error_details = None
    # try:
    #     lines = config_str.split('\n')
    #     for i, line in enumerate(lines, 1):
    #         try:
    #             json.loads(line)
    #         except json.JSONDecodeError as e:
    #             error_details = f"Line {i} has JSON error: {line[:100]}..."
    #             logger.error(f"JSON parsing failed for '{video_title}': {error_details}")
    #             break
    # except Exception as e:
    #     logger.debug(f"Line-by-line analysis failed: {e}")
    
    # Raise exception with detailed error message
    error_msg = f"Failed to parse json2video config for '{video_title}'"
    # if error_details:
    #     error_msg += f": {error_details}"
    # else:
    error_msg += ": All JSON parsing strategies failed"
    
    Logger.error(error_msg)
    # raise JSON2VideoConfigParseError(error_msg)
    return {}

def test_json2video_configs():
    """Test loading autodraft output and parsing json2video configs"""
    
    # Path to the autodraft output file
    autodraft_file = "resources/autodraft_output.enhanced.json"
    
    try:
        # Load the autodraft output
        print(f"🔍 Loading autodraft output from: {autodraft_file}")
        with open(autodraft_file, 'r') as f:
            autodraft_data = json.load(f)
        
        print(f"✅ Successfully loaded autodraft data")
        
        # Extract parsed output
        parsed_output = autodraft_data.get('parsed_output')
        if not parsed_output or 'videos' not in parsed_output:
            print("❌ No videos found in parsed_output")
            return
        
        videos = parsed_output['videos']
        print(f"📹 Found {len(videos)} videos to process")
        print("=" * 80)
        
        # Process each video
        for i, video in enumerate(videos, 1):
            print(f"\n🎬 Video {i}: {video.get('title', 'No Title')}")
            print(f"📝 Caption: {video.get('video_caption', 'No Caption')[:100]}...")
            
            # Get the json2video config string
            config_str = video.get('json2video_config_str')
            if not config_str:
                print("❌ No json2video_config_str found")
                continue
            
            # Parse the config using our dedicated method
            config_json = parse_json2video_config(config_str, video.get('title', 'Unknown'))
            
            if config_json is None:
                print(f"❌ Failed to parse json2video_config_str")
                print(f"   Raw string preview: {config_str[:200]}...")
                
                # Show more details about the problematic string
                print(f"   String length: {len(config_str)} characters")
                print(f"   First 500 chars: {repr(config_str[:500])}")
                if len(config_str) > 500:
                    print(f"   Last 500 chars: {repr(config_str[-500:])}")
                continue
            
            # Pretty print the parsed config
            print(f"✅ Successfully parsed json2video config")
            
            print(f"   📊 Quality: {config_json.get('quality', 'Unknown')}")
            print(f"   📝 Draft: {config_json.get('draft', 'Unknown')}")
            print(f"   🎬 Scenes: {len(config_json.get('scenes', []))}")
            print(f"   🎵 Elements: {len(config_json.get('elements', []))}")
            print(f"   📱 Resolution: {config_json.get('resolution', 'Unknown')}")
            print(f"   🎞️ FPS: {config_json.get('fps', 'Unknown')}")
            
            # Show scene details
            scenes = config_json.get('scenes', [])
            for j, scene in enumerate(scenes, 1):
                print(f"   🎭 Scene {j}: {scene.get('comment', 'No comment')}")
                elements = scene.get('elements', [])
                for k, element in enumerate(elements, 1):
                    element_type = element.get('type', 'Unknown')
                    element_src = element.get('src', 'No source')
                    print(f"     📹 Element {k}: {element_type} - {element_src[:60]}...")
            
            # Show global elements
            global_elements = config_json.get('elements', [])
            if global_elements:
                print(f"   🌍 Global Elements:")
                for j, element in enumerate(global_elements, 1):
                    element_type = element.get('type', 'Unknown')
                    if element_type == 'audio':
                        src = element.get('src', 'No source')
                        print(f"     🎵 Audio {j}: {src[:60]}...")
                    elif element_type == 'voice':
                        text = element.get('text', 'No text')
                        print(f"     🗣️ Voice {j}: {text[:60]}...")
                    else:
                        print(f"     📄 {element_type} {j}: {str(element)[:60]}...")
            
            # Save formatted JSON to file
            output_file = f"formatted_config_video_{i}.json"
            with open(output_file, 'w') as f:
                json.dump(config_json, f, indent=2)
            print(f"💾 Formatted config saved to: {output_file}")
        
        print("\n" + "=" * 80)
        print("✅ Test completed!")
        
    except FileNotFoundError:
        print(f"❌ File not found: {autodraft_file}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse autodraft file: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_json2video_configs()
