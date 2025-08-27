#!/usr/bin/env python3
"""
Main entrypoint for the enhanced autopost system
"""

import openai
import json
import argparse
from pathlib import Path
from pydantic import BaseModel
from typing import List
from config import ConfigManager
from autopotter_tools.parse_json2video_configs import parse_json2video_config


class DraftVideo(BaseModel):
    title: str
    video_strategy: str  
    video_caption: str
    json2video_config_str: str
    
    def get_json2video_config(self):
        success, config_json, error_message = parse_json2video_config(self.json2video_config_str, self.title)
        if success:
            if error_message:
                print(f"⚠️ Fixed json2video config for '{self.title}': {error_message}")
            return config_json
        else:
            print(f"❌ Failed to parse json2video config for '{self.title}': {error_message}")
            return {}

class DraftVideoList(BaseModel):
    videos: List[DraftVideo]
    
    def get_json2video_config(self):
        return [video.get_json2video_config() for video in self.videos]


def resolve_file_inclusions(config: ConfigManager) -> str:
    """
    Resolve gpt_responses_other_files_to_include and replace <<filename>> placeholders
    with the actual file contents. Returns the resolved text to append to instructions.
    """
    other_files = config.get('gpt_responses_other_files_to_include', {})
    resolved_text = ""
    
    for key, filepath in other_files.items():
        try:
            if Path(filepath).exists():
                with open(filepath, 'r') as f:
                    content = f.read()
                resolved_text += f"\n\n{key.upper()}:\n{content}"
            else:
                print(f"⚠️ Warning: File {filepath} not found for {key}")
        except Exception as e:
            print(f"❌ Error reading file {filepath}: {e}")
    
    return resolved_text


def main_autodraft(outfile, config_file, prompt_override):
    
    print(f"📁 Output will be saved to: {outfile}")
    print(f"⚙️ Using config file: {config_file}")
    
    # Load configuration
    config = ConfigManager(config_file)
    
    # Initialize OpenAI client
    client = openai.OpenAI()
    
    # Get the base instructions from config
    base_instructions = config.get('gpt_responses_instructions', '')
    
    # Resolve file inclusions and append to instructions
    file_inclusions = resolve_file_inclusions(config)
    full_instructions = base_instructions + file_inclusions

    with open("full_instructions.txt", "+w") as f:
        f.write(full_instructions)
    
    # Use custom prompt if provided, otherwise use config default
    prompt = prompt_override if prompt_override else config.get('gpt_user_prompt_prompt')
    
    print(f"📝 Using prompt: {prompt}")
    
    # Check if we should include previous response context based on config
    previous_response_id = config.get('gpt_previous_response_id')
    if config.get('gpt_use_previous_response_id', False) and previous_response_id:
        print(f"🔄 Including previous response context: {previous_response_id}")
        # You could optionally fetch the previous response here and include it in the prompt
        # For now, we'll just note that it's available
        prompt += f"\n\nNote: This is a follow-up to response {previous_response_id}"
    
    # Send request using Responses API with structured output
    response = client.responses.parse(
        model=config.get('gpt_model', 'gpt-4o-2024-08-06'),
        input=[
            {"role": "developer", "content": full_instructions},
            {"role": "user", "content": prompt}
        ],
        text_format=DraftVideoList,
        # previous_response_id=previous_response_id
    )
    
    # Extract response text and parsed output
    response_text = response.output[0].content[0].text
    parsed_output = response.output_parsed
    
    # Display response
    print("\nGPT Parsed Output ------------------------------")
    #print(parsed_output)
    # Print only the video title and caption(s) instead of the whole parsed_output
    if parsed_output and hasattr(parsed_output, "videos"):
        for idx, video in enumerate(parsed_output.videos):
            title = getattr(video, "title", "<No Title>")
            caption = getattr(video, "video_caption", "<No Caption>")
            print(f"Video {idx+1}:")
            print(f"  Title: {title}")
            print(f"  Caption: {caption}\n")
    else:
        print("No videos found in parsed_output.")
    print("\nJSON2Video Config ------------------------------")
    # print(parsed_output.get_json2video_config())
    print("\n\nResponse ID -- ", response.id)

    # Always save response ID to config for future reference
    config.set('gpt_previous_response_id', response.id)
    config.save_config()

    parsed_json2video_configs = parsed_output.get_json2video_config() if parsed_output else None

    # Save to file
    with open(outfile, "w") as f:
        json.dump({
            "prompt": prompt,
            "response": response_text,
            "parsed_output": parsed_output.model_dump() if parsed_output else None,
            "parsed_json2video_configs": parsed_json2video_configs,
            "model": config.get('gpt_model', 'gpt-4o-2024-08-06'),
            "response_id": response.id
        }, f, indent=2)
    
    print(f"\nResponse saved to {outfile}")
    print(f"Response ID saved to config: {response.id}")

    # return parsed_json2video_configs

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced autopost system main entrypoint')
    parser.add_argument('--outfile', '-o',
                       default='autodraft_output.enhanced.json',
                       help='Output file path (default: autodraft.enhanced.json)')
    parser.add_argument('--prompt', '-p',
                       default=None,
                       help='Custom prompt for GPT (uses config default if not specified)')
    parser.add_argument('--config', '-c',
                       default='autopost_config.enhanced.json',
                       help='Config file path (default: autopost_config.enhanced.json)')
    args = parser.parse_args()
    
    main_autodraft(args.outfile, args.config, args.prompt)
