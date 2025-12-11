#!/usr/bin/env python3
"""
Main entrypoint for the enhanced autopost system
"""

import json
import argparse
from pathlib import Path
from pydantic import BaseModel
from typing import Any, List
from config import get_config, ConfigManager
from datetime import datetime
from autopotter_tools.parse_json2video_configs import parse_json2video_config
from autopotter_tools.gpt_api import GPTAPI
from autopotter_tools.simplelogger import Logger
from autopotter_tools.agent_db_tools import AgentDBTools

# Logger.setup(loglevel='debug')

class DraftVideo(BaseModel):
    title: str
    video_strategy: str  
    video_caption: str
    json2video_config_str: str #dict # shouldn't this be a dict?!
    reasoning: str
    
    def get_json2video_config(self):
        config_json = parse_json2video_config(self.json2video_config_str, self.title)
        if config_json is None:
            Logger.error(f"Failed to parse json2video config for '{self.title}'")
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
    other_files = config.get('gpt_responses_other_files_to_include', {})
    resolved_text = ""
    
    for key, filepath in other_files.items():
        try:
            if Path(filepath).exists():
                with open(filepath, 'r') as f:
                    content = f.read()
                resolved_text += f"\n\n{key.upper()}:\n{content}"
            else:
                Logger.warning(f"File {filepath} not found for {key}")
        except Exception as e:
            Logger.error(f"Error reading file {filepath}: {e}")
    
    return resolved_text


def main_autodraft(outfile, config_file, prompt_override=None, minimal=False):
    # Load configuration first to initialize logging
    # config = ConfigManager(config_file)
    config = get_config(config_path=config_file)
    
    Logger.info(f"Output will be saved to: {outfile}")
    
    # Use custom prompt if provided, otherwise use config default
    prompt = prompt_override if prompt_override else config.get('gpt_user_prompt_prompt')
    
    Logger.info(f"Using prompt: {prompt}")
    
    if minimal:
        Logger.info("Minimal mode: Skipping file inclusions and base instructions")
        full_instructions = ""
    else:
        # Get the base instructions from config
        base_instructions = config.get('gpt_responses_instructions', '')
        
        # Resolve file inclusions and append to instructions
        file_inclusions = resolve_file_inclusions(config)
        full_instructions = base_instructions + file_inclusions

    with open("full_instructions.txt", "+w") as f:
        f.write(full_instructions)
        Logger.info(f"Full instructions written to full_instructions.txt: {full_instructions}")
    
    
    # Initialize GPT API with response ID tracking enabled
    api = GPTAPI(
        model=config.get('gpt_model'),
        use_previous_response_id=config.get('gpt_use_previous_response_id'),
        previous_response_id=config.get('gpt_previous_response_id', None)
    )

    # Agent tool-calling parameters
    max_tool_calls = int(config.get("agentdraft_tool_max_calls", 5))
    cap_message = config.get(
        "agentdraft_tool_cap_message",
        "Tool call limit reached; please complete your response.",
    )
    Logger.info(
        f"[agentdraft] Tool loop configured: max_tool_calls={max_tool_calls}, "
        f"cap_message='{cap_message}'"
    )

    # Build a simple loop to allow bounded tool calls; when the cap is hit we
    # add an extra user message instructing the model to finish without more tools.
    def _run_with_tools() -> Any:
        db_tools = AgentDBTools(config_file)
        tools = db_tools.get_agent_tool_defs()  # already in Responses API format
        Logger.info(f"[agentdraft] Loaded {len(tools)} tools for the agent.")

        messages = [
            {"role": "developer", "content": [{"type": "input_text", "text": full_instructions}]},
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ]

        tool_calls = 0
        response = None
        while True:
            Logger.debug(
                f"[agentdraft] Dispatching request with {len(messages)} messages "
                f"and {tool_calls} tool calls so far."
            )
            response = api.client.responses.parse(
                model=config.get('gpt_model'),
                input=messages,
                tools=tools,
                parallel_tool_calls=False,
                text_format=DraftVideoList,  # ensure structured output
            )
            outputs = getattr(response, "output", []) or []

            Logger.info(f"Outputs: {[getattr(item, 'type', None) for item in outputs]}")
            # for item in outputs:
            #     Logger.info(f"Output Types: {getattr(item, 'type', None)}")

            processed_calls = 0
            cap_added = False
            tool_results: List[dict] = []
            for item in outputs:
                item_type = getattr(item, "type", None)
                if item_type not in ("tool_call", "function_call"):
                    continue
                if tool_calls >= max_tool_calls:
                    break

                tool_calls += 1
                processed_calls += 1
                name = getattr(item, "name", "")
                raw_arguments = getattr(item, "arguments", {}) or {}
                if isinstance(raw_arguments, str):
                    try:
                        arguments = json.loads(raw_arguments)
                    except Exception:
                        arguments = {}
                else:
                    arguments = raw_arguments
                Logger.info(f"Tool call {tool_calls}: {name} args={arguments}")
                Logger.debug(f"Raw tool_call item: {item}")

                if name == "search_keyword":
                    result = db_tools.search_keyword(
                        keyword=arguments.get("keyword", ""),
                        limit=int(arguments.get("limit", 10) or 10),
                    )
                    Logger.info(
                        f"[agentdraft] Executed search_keyword -> {len(result)} results"
                    )
                    Logger.debug(f"[agentdraft] search_keyword result: {result}")
                elif name == "search_semantic":
                    result = db_tools.search_semantic(
                        text=arguments.get("text", ""),
                        limit=int(arguments.get("limit", 10) or 10),
                    )
                    Logger.info(
                        f"[agentdraft] Executed search_semantic -> {len(result)} results"
                    )
                    Logger.debug(f"[agentdraft] search_semantic result: {result}")
                else:
                    result = {"error": f"Unknown tool {name}"}

                tool_results.append(
                    {
                        "tool_call_id": getattr(item, "id", None),
                        "name": name,
                        "arguments": arguments,
                        "result": result,
                    }
                )

            if tool_calls >= max_tool_calls and not cap_added:
                Logger.info(
                    "[agentdraft] Tool cap reached; adding cap message and exiting tool loop."
                )
                messages.append(
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": cap_message}],
                    }
                )
                cap_added = True

            if processed_calls:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": json.dumps(
                                    {"tool_results": tool_results}, ensure_ascii=False
                                ),
                            }
                        ],
                    }
                )

            if tool_calls >= max_tool_calls:
                # Force a final turn without tools to get the model to complete.
                Logger.info("[agentdraft] Forcing final completion without tools.")
                response = api.client.responses.parse(
                    model=config.get('gpt_model'),
                    input=messages,
                    tools=[],
                    text_format=DraftVideoList,
                )
                break

            if processed_calls == 0:
                break

        return response

    response = _run_with_tools()

    parsed_output = getattr(response, "output_parsed", None)
    
    # Extract response text for saving
    response_text = None
    if hasattr(response, "output") and response.output:
        for item in response.output:
            if hasattr(item, "content") and item.content and len(item.content) > 0:
                if hasattr(item.content[0], "text"):
                    response_text = item.content[0].text
                    Logger.info(f"Response text: {response_text}")
                    break
    
    # Display response
    Logger.info("GPT Parsed Output ------------------------------")
    # Log only the video title and caption(s) instead of the whole parsed_output
    if parsed_output and hasattr(parsed_output, "videos"):
        for idx, video in enumerate(parsed_output.videos):
            title = getattr(video, "title", "<No Title>")
            caption = getattr(video, "video_caption", "<No Caption>")
            Logger.info(f"Video {idx+1}:")
            Logger.info(f"  Title: {title}")
            Logger.info(f"  Caption: {caption}")
    else:
        Logger.warning("No videos found in parsed_output.")
        Logger.warning(f"Parsed output: {parsed_output}")
        Logger.warning(f"Response: {response}")
    Logger.info("JSON2Video Config ------------------------------")
    # Logger.debug(parsed_output.get_json2video_config())
    Logger.info(f"Response ID: {response.id}")

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
    
    Logger.info(f"Response saved to {outfile}")
    Logger.info(f"Response ID saved to config: {response.id}")

    # return parsed_json2video_configs

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced autopost system main entrypoint')
    parser.add_argument('--outfile', '-o',
                       default='resources/autodraft_output.json',
                       help='Output file path (default: autodraft.json)')
    parser.add_argument('--prompt', '-p',
                       default=None,
                       help='Custom prompt for GPT (uses config default if not specified)')
    parser.add_argument('--config', '-c',
                       default='autopost_config.json',
                       help='Config file path (default: autopost_config.json)')
    parser.add_argument('--minimal', '-m',
                       action='store_true',
                       help='Minimal mode: Skip file inclusions and base instructions, only send prompt as user_instruction')
    args = parser.parse_args()
    
    main_autodraft(args.outfile, args.config, args.prompt, args.minimal)
