#!/usr/bin/env python3
"""
Quick test script to load autodraft output and convert json2video_config_str to formatted JSON
"""

import json
import sys
import re
from pathlib import Path

def parse_json2video_config(config_str, video_title="Unknown"):
    """
    Parse and validate a json2video config string with multiple fallback strategies.
    
    Args:
        config_str: The JSON string to parse
        video_title: Title of the video for error reporting
        
    Returns:
        Tuple of (success: bool, config_json: dict, error_message: str)
    """
    if not config_str:
        return False, None, "No config string provided"
    
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
            config_json = json.loads(repair_func(config_str))
            return True, config_json, f"Fixed via {strategy_name}" if strategy_name != "direct parsing" else None
        except json.JSONDecodeError:
            continue
    
    # If all strategies fail, identify the specific issue
    try:
        lines = config_str.split('\n')
        for i, line in enumerate(lines, 1):
            try:
                json.loads(line)
            except json.JSONDecodeError:
                return False, None, f"Line {i} has JSON error: {line[:100]}..."
    except Exception:
        pass
    
    return False, None, "All JSON parsing strategies failed"

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
            success, config_json, error_message = parse_json2video_config(config_str, video.get('title', 'Unknown'))
            
            if success:
                # Pretty print the parsed config
                print(f"✅ Successfully parsed json2video config")
                if error_message and "Fixed" in error_message:
                    print(f"   🔧 {error_message}")
                
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
                
            else:
                print(f"❌ Failed to parse json2video_config_str: {error_message}")
                print(f"   Raw string preview: {config_str[:200]}...")
                
                # Show more details about the problematic string
                print(f"   String length: {len(config_str)} characters")
                print(f"   First 500 chars: {repr(config_str[:500])}")
                if len(config_str) > 500:
                    print(f"   Last 500 chars: {repr(config_str[-500:])}")
        
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
