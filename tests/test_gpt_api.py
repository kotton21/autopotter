#!/usr/bin/env python3
"""
Test script for GPTAPI class.
Demonstrates a conversation flow with 3 canned prompts.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from autopotter_tools.gpt_api import GPTAPI
from autopotter_tools.logger import initialize_logging



def main():
    """Test the GPTAPI class with a short conversation."""
    
    # Initialize logging
    initialize_logging({'log_level': 'INFO', 'log_console_output': True})
    
    print("=" * 60)
    print("GPTAPI Test - Conversation Flow")
    print("=" * 60)
    
    # Initialize API with new conversation (use_previous_response_id=True, no previous_response_id)
    print("\n📝 Initializing GPTAPI with new conversation...")
    print("   - use_previous_response_id: True")
    print("   - previous_response_id: None (new conversation)")
    
    try:
        api = GPTAPI(
            model="gpt-4o-2024-08-06",
            use_previous_response_id=True,
            previous_response_id=None
        )
        print("✅ GPTAPI initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize GPTAPI: {e}")
        return 1
    
    # Define 3 canned prompts for the conversation
    prompts = [
        "Hello! My name is Karl. I'm interested in learning about pottery. Can you tell me what makes a good ceramic glaze?",
        "That's helpful! Can you recommend any beginner-friendly pottery techniques?",
        "Thanks! Remind me what name I used to introduce myself and tell me more"
    ]
    
    # Carry out the conversation
    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'=' * 60}")
        print(f"Message {i} of {len(prompts)}")
        print(f"{'=' * 60}")
        print(f"📤 Sending: {prompt[:80]}..." if len(prompt) > 80 else f"📤 Sending: {prompt}")
        
        if api.previous_response_id:
            print(f"🔄 Using previous response ID: {api.previous_response_id}")
        
        try:
            # Send prompt and wait for response
            start_time = time.time()
            response = api.prompt(user_instructions=prompt)
            elapsed_time = time.time() - start_time
            
            # Extract response text
            if hasattr(response, 'output') and response.output:
                response_text = response.output[0].content[0].text
            else:
                response_text = "No response text available"
            
            # Extract parsed output if available
            parsed_output = None
            if hasattr(response, 'output_parsed'):
                parsed_output = response.output_parsed
            
            # Display results
            print(f"✅ Response received in {elapsed_time:.2f} seconds")
            print(f"📋 Response ID: {response.id}")
            
            if api.use_previous_response_id and api.previous_response_id:
                print(f"💾 Saved response ID for next message: {api.previous_response_id}")
            
            print(f"\n📥 Response text (first 200 chars):")
            print(f"   {response_text[:200]}..." if len(response_text) > 200 else f"   {response_text}")
            
            if parsed_output:
                print(f"\n📦 Parsed output available: {type(parsed_output).__name__}")
            
            # Wait a moment before next message
            if i < len(prompts):
                print("\n⏳ Waiting 2 seconds before next message...")
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Error during API call: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    print("\n" + "=" * 60)
    print("✅ Conversation test completed successfully!")
    print("=" * 60)
    
    if api.previous_response_id:
        print(f"\n📝 Final response ID: {api.previous_response_id}")
        print("   (This could be used to continue the conversation later)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

