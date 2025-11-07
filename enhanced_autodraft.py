#!/usr/bin/env python3
"""
Main entrypoint for the enhanced autopost system
"""

import json
import argparse
from pathlib import Path
from pydantic import BaseModel
from typing import List
from config import ConfigManager
from datetime import datetime
from autopotter_tools.parse_json2video_configs import parse_json2video_config
from autopotter_tools.gpt_api import GPTAPI
from autopotter_tools.logger import get_logger


class DraftVideo(BaseModel):
    title: str
    video_strategy: str  
    video_caption: str
    json2video_config_str: str #dict # shouldn't this be a dict?!
    
    def get_json2video_config(self):
        logger = get_logger('enhanced_autodraft')
        config_json = parse_json2video_config(self.json2video_config_str, self.title)
        if config_json is None:
            logger.error(f"Failed to parse json2video config for '{self.title}'")
        return config_json

class DraftVideoList(BaseModel):
    videos: List[DraftVideo]
    
    def get_json2video_config(self):
        return [video.get_json2video_config() for video in self.videos]


def resolve_file_inclusions(config: ConfigManager) -> str:
    """
    Resolve gpt_responses_other_files_to_include and replace <<filename>> placeholders
    with the actual file contents. Returns the resolved text to append to instructions.
    """
    logger = get_logger('enhanced_autodraft')
    other_files = config.get('gpt_responses_other_files_to_include', {})
    resolved_text = ""
    
    for key, filepath in other_files.items():
        try:
            if Path(filepath).exists():
                with open(filepath, 'r') as f:
                    content = f.read()
                resolved_text += f"\n\n{key.upper()}:\n{content}"
            else:
                logger.warning(f"File {filepath} not found for {key}")
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
    
    return resolved_text


def main_autodraft(outfile, config_file, prompt_override=None, minimal=False):
    # Load configuration first to initialize logging
    config = ConfigManager(config_file)
    logger = get_logger('enhanced_autodraft')
    
    logger.info(f"Output will be saved to: {outfile}")
    
    # Use custom prompt if provided, otherwise use config default
    prompt = prompt_override if prompt_override else config.get('gpt_user_prompt_prompt')
    
    logger.info(f"Using prompt: {prompt}")
    
    if minimal:
        logger.info("Minimal mode: Skipping file inclusions and base instructions")
        full_instructions = ""
    else:
        # Get the base instructions from config
        base_instructions = config.get('gpt_responses_instructions', '')
        
        # Resolve file inclusions and append to instructions
        file_inclusions = resolve_file_inclusions(config)
        full_instructions = base_instructions + file_inclusions

    with open("full_instructions.txt", "+w") as f:
        f.write(full_instructions)
    
    
    # Initialize GPT API with response ID tracking enabled
    api = GPTAPI(
        model=config.get('gpt_model'),
        use_previous_response_id=config.get('gpt_use_previous_response_id'),
        previous_response_id=config.get('gpt_previous_response_id', None)
    )
    
    
    response = api.prompt(
        developer_instructions=full_instructions,
        text_format=DraftVideoList,
        user_instructions=prompt
    )
    
    parsed_output = response.output_parsed
    
    # Extract response text for saving
    response_text = None
    if hasattr(response, "output") and response.output:
        for item in response.output:
            if hasattr(item, "content") and item.content and len(item.content) > 0:
                if hasattr(item.content[0], "text"):
                    response_text = item.content[0].text
                    logger.info(f"Response text: {response_text}")
                    break
    
    # Display response
    logger.info("GPT Parsed Output ------------------------------")
    # Log only the video title and caption(s) instead of the whole parsed_output
    if parsed_output and hasattr(parsed_output, "videos"):
        for idx, video in enumerate(parsed_output.videos):
            title = getattr(video, "title", "<No Title>")
            caption = getattr(video, "video_caption", "<No Caption>")
            logger.info(f"Video {idx+1}:")
            logger.info(f"  Title: {title}")
            logger.info(f"  Caption: {caption}")
    else:
        logger.warning("No videos found in parsed_output.")
    logger.info("JSON2Video Config ------------------------------")
    # logger.debug(parsed_output.get_json2video_config())
    logger.info(f"Response ID: {response.id}")

    # Save response ID to config for future reference (GPTAPI already saved it internally)
    if config.get('gpt_use_previous_response_id'):
        config.set('gpt_previous_response_id', response.id)
        config.set('gpt_previous_response_date', datetime.now().isoformat())
    # config.save_config()


    parsed_json2video_configs = parsed_output.get_json2video_config() if parsed_output else None

    # Save to file
    with open(outfile, "w") as f:
        json.dump({
            "prompt": prompt,
            "response": response_text,
            "parsed_output": parsed_output.model_dump() if parsed_output else None,
            "parsed_json2video_configs": parsed_json2video_configs,
            "model": config.get('gpt_model'),
            "response_id": response.id
        }, f, indent=2)
    
    logger.info(f"Response saved to {outfile}")
    logger.info(f"Response ID saved to config: {response.id}")

    # return parsed_json2video_configs

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced autopost system main entrypoint')
    parser.add_argument('--outfile', '-o',
                       default='resources/autodraft_output.enhanced.json',
                       help='Output file path (default: autodraft.enhanced.json)')
    parser.add_argument('--prompt', '-p',
                       default=None,
                       help='Custom prompt for GPT (uses config default if not specified)')
    parser.add_argument('--config', '-c',
                       default='autopost_config.enhanced.json',
                       help='Config file path (default: autopost_config.enhanced.json)')
    parser.add_argument('--minimal', '-m',
                       action='store_true',
                       help='Minimal mode: Skip file inclusions and base instructions, only send prompt as user_instruction')
    args = parser.parse_args()
    
    main_autodraft(args.outfile, args.config, args.prompt, args.minimal)
