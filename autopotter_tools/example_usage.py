#!/usr/bin/env python3
"""
Example usage of the generic GPTThreadManager.
This demonstrates how the interface can be used for various purposes.
"""

import sys
import os

# Add parent directory to path to import config and logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autopotter_tools.gpt_thread_manager import GPTThreadManager

def example_basic_usage():
    """Example of basic GPT Thread Manager usage."""
    print("=== Basic Usage Example ===")
    
    try:
        # Initialize the manager
        manager = GPTThreadManager()
        
        # Get thread information
        thread_info = manager.get_thread_info()
        print(f"Thread ID: {thread_info['thread_id']}")
        print(f"Assistant configured: {thread_info['assistant_configured']}")
        
        # Send a simple prompt
        if thread_info['assistant_configured']:
            response = manager.prompt("Hello! Can you help me with a question?")
            print(f"Response: {response}")
        else:
            print("No assistant configured - prompt functionality limited")
            
    except Exception as e:
        print(f"Error in basic usage example: {e}")

def example_file_upload():
    """Example of uploading files for context."""
    print("\n=== File Upload Example ===")
    
    try:
        manager = GPTThreadManager()
        
        # Example file paths (these would be real files in practice)
        example_files = [
            "example_data.json",
            "context_document.txt"
        ]
        
        # Check if files exist before uploading
        existing_files = [f for f in example_files if os.path.exists(f)]
        
        if existing_files:
            print(f"Uploading {len(existing_files)} files...")
            file_ids = manager.upload_files(existing_files)
            print(f"Uploaded {len(file_ids)} files with IDs: {file_ids}")
            
            # Clean up uploaded files
            manager.cleanup_files(file_ids)
            print("Files cleaned up")
        else:
            print("No example files found - skipping upload test")
            
    except Exception as e:
        print(f"Error in file upload example: {e}")

def example_custom_prompts():
    """Example of using custom prompts for different purposes."""
    print("\n=== Custom Prompts Example ===")
    
    try:
        manager = GPTThreadManager()
        
        # Example 1: Content analysis
        content_prompt = "Analyze the following content and provide insights: [content here]"
        print(f"Content analysis prompt: {content_prompt}")
        
        # Example 2: Data processing
        data_prompt = "Process this data and extract key metrics: [data here]"
        print(f"Data processing prompt: {data_prompt}")
        
        # Example 3: Creative writing
        creative_prompt = "Write a creative story based on: [theme here]"
        print(f"Creative writing prompt: {creative_prompt}")
        
        print("These prompts can be used with manager.prompt() method")
        
    except Exception as e:
        print(f"Error in custom prompts example: {e}")

def example_thread_management():
    """Example of thread management features."""
    print("\n=== Thread Management Example ===")
    
    try:
        manager = GPTThreadManager()
        
        # Get current thread info
        thread_info = manager.get_thread_info()
        print(f"Current thread: {thread_info['thread_id']}")
        
        # The manager automatically handles:
        # - Creating new threads when needed
        # - Loading existing threads from config
        # - Fallback thread creation on errors
        
        print("Thread management is handled automatically")
        
    except Exception as e:
        print(f"Error in thread management example: {e}")

def main():
    """Run all examples."""
    print("GPTThreadManager Usage Examples")
    print("=" * 40)
    
    examples = [
        example_basic_usage,
        example_file_upload,
        example_custom_prompts,
        example_thread_management
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Example {example.__name__} failed: {e}")
        
        print()  # Add spacing between examples
    
    print("=" * 40)
    print("Examples completed!")
    print("\nKey points:")
    print("- GPTThreadManager is a generic interface for any GPT assistant use case")
    print("- It handles thread lifecycle, file uploads, and basic prompting")
    print("- Business logic (like video generation) should be implemented in separate modules")
    print("- The interface is designed to be reusable across different applications")

if __name__ == "__main__":
    main()
