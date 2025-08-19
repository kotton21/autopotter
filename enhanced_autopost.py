#!/usr/bin/env python3
"""
Enhanced Video Generation System - Phase 4
Primary entry point for AI-driven video proposal generation using GPT Responses API.

This module implements the main generation flow:
1. Load configuration and check parameters
2. Gather Instagram analytics (if enabled)
3. Gather GCS file inventory
4. Initialize GPT Responses Manager
5. Query GPT with available data and prompt intent
6. Print results

Usage:
    python enhanced_autopost.py [--config CONFIG_FILE] [--draft-prompt PROMPT_OVERRIDE]
"""

import os
import sys
import argparse
import json
from typing import Dict, Any, Optional

# Add autopotter_tools to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'autopotter_tools'))

from autopotter_tools.logger import get_logger
from autopotter_tools.instagram_analytics import InstagramAnalyticsManager
from autopotter_tools.gcs_manager import GCSManager
from autopotter_tools.gpt_responses_manager import GPTResponsesManager
from config import get_config

# Default config file path
DEFAULT_CONFIG_PATH = "autopost_config.enhanced.json"

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load and validate configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If required configuration is missing
    """
    logger = get_logger('enhanced_autopost')
    
    try:
        config_manager = get_config(config_path)
        config = config_manager.config
        
        # Check for required configuration sections
        required_sections = ['openai_api_key', 'gcs_bucket', 'gcs_api_key_path']
        missing_sections = [section for section in required_sections if not config.get(section)]
        
        if missing_sections:
            raise ValueError(f"Missing required configuration: {', '.join(missing_sections)}")
        
        logger.info(f"Configuration loaded successfully from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

def gather_instagram_analytics(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Gather Instagram analytics if enabled in configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Instagram analytics data or None if disabled
    """
    logger = get_logger('enhanced_autopost')
    
    if not config.get('include_ig_insights_in_prompt', False):
        logger.info("Instagram insights collection disabled in configuration")
        return None
    
    try:
        logger.info("Gathering Instagram analytics...")
        analytics_manager = InstagramAnalyticsManager()
        analytics_data = analytics_manager.export_to_json()
        logger.info("Instagram analytics gathered successfully")
        return analytics_data
        
    except Exception as e:
        logger.error(f"Failed to gather Instagram analytics: {e}")
        return None

def gather_gcs_inventory(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gather GCS file inventory.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        GCS file inventory data
    """
    logger = get_logger('enhanced_autopost')
    
    try:
        logger.info("Gathering GCS file inventory...")
        gcs_manager = GCSManager()
        inventory_data = gcs_manager.generate_inventory()
        logger.info("GCS file inventory gathered successfully")
        return inventory_data
        
    except Exception as e:
        logger.error(f"Failed to gather GCS inventory: {e}")
        raise

def query_gpt_responses(config: Dict[str, Any], 
                       ig_analytics: Optional[Dict[str, Any]], 
                       gcs_inventory: Dict[str, Any], 
                       draft_prompt: str) -> str:
    """
    Query GPT using the Responses API with available data and prompt intent.
    
    Args:
        config: Configuration dictionary
        ig_analytics: Instagram analytics data (optional)
        gcs_inventory: GCS file inventory data
        draft_prompt: Custom prompt intent override
        
    Returns:
        GPT response
    """
    logger = get_logger('enhanced_autopost')
    
    try:
        logger.info("Initializing GPT Responses Manager...")
        responses_manager = GPTResponsesManager()
        
        # Prepare context data for the assistant
        context_data = {
            "gcs_inventory": gcs_inventory#,
            # "draft_prompt": draft_prompt
        }
        
        if ig_analytics:
            context_data["instagram_analytics"] = ig_analytics
            logger.info("Including Instagram analytics in context")
        
        logger.info("Querying GPT with context data...")
        response = responses_manager.prompt(draft_prompt, context_data)
        
        logger.info("GPT response received successfully")
        return response
        
    except Exception as e:
        logger.error(f"Failed to query GPT: {e}")
        raise

def main():
    """Main entry point for enhanced autopost."""
    parser = argparse.ArgumentParser(
        description="Enhanced Video Generation System - AI-driven content proposal generation"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default=DEFAULT_CONFIG_PATH, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--draft-prompt", 
        type=str, 
        help="Override draft prompt from configuration"
    )
    
    args = parser.parse_args()
    
    # Initialize logging
    logger = get_logger('enhanced_autopost')
    logger.info("Starting Enhanced Video Generation System")
    
    try:
        # 1. Load configuration and check parameters
        logger.info("Step 1: Loading configuration...")
        config = load_config(args.config)
        
        # 2. Gather Instagram analytics if enabled
        logger.info("Step 2: Gathering Instagram analytics...")
        ig_analytics = gather_instagram_analytics(config)
        
        # 3. Gather GCS file inventory
        logger.info("Step 3: Gathering GCS file inventory...")
        gcs_inventory = gather_gcs_inventory(config)
        
        # 4. Initialize GPT Responses Manager
        logger.info("Step 4: Initializing GPT Responses Manager...")
        
        # 5. Query GPT with available data and prompt intent
        logger.info("Step 5: Querying GPT with context data...")
        
        # Use custom prompt intent if provided, otherwise use first from config
        if args.draft_prompt:
            draft_prompt = args.draft_prompt
            logger.info(f"Using custom prompt intent: {draft_prompt}")
        else:
            draft_prompt = config.get('gpt_draft_prompt', "")
            if draft_prompt:
                logger.info(f"Using default prompt intent: {draft_prompt}")
            else:
                logger.error("No draft prompt found in configuration and no --draft-prompt parameter provided")
                raise ValueError("Draft prompt is required. Either configure 'gpt_draft_prompt' in the config file or use --draft-prompt parameter")
        
        # Query GPT using the Responses API
        response = query_gpt_responses(config, ig_analytics, gcs_inventory, draft_prompt)
        
        # 6. Print results
        logger.info("Step 6: Displaying results...")
        print("\n" + "="*80)
        print("ENHANCED VIDEO GENERATION RESULTS")
        print("="*80)
        print(f"\nPrompt Intent: {draft_prompt}")
        print("\nGPT Response:")
        print("-" * 40)
        print(response)
        print("="*80)
        
        logger.info("Enhanced video generation completed successfully")
        
    except Exception as e:
        logger.error(f"Enhanced video generation failed: {e}")
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
