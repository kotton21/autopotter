import openai
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports when running as script
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import get_logger

class GPTThreadManager:
    """
    Generic interface to a GPT assistant.
    Handles thread lifecycle, file uploads, context management, and content generation.
    Can be used for any purpose that requires GPT assistant interaction.
    """
    
    def __init__(self, config_path: str = "autopost_config.enhanced.json"):
        self.logger = get_logger('gpt_thread_manager')
        self.logger.info("Initializing GPTThreadManager...")
        
        # Load configuration using the new config system
        from config import get_config
        self.config_manager = get_config(config_path)
        self.openai_config = self.config_manager.get_openai_config()
        
        # Validate required configuration
        if not self.openai_config.get('api_key'):
            raise ValueError("OpenAI API key is required")
        
        if not self.openai_config.get('assistant_id'):
            self.logger.warning("No assistant_id configured. Some features may not work properly.")
        
        self.client = openai.OpenAI(api_key=self.openai_config['api_key'])
        self.thread_id = None
        self.assistant_id = self.openai_config.get('assistant_id')
        
        # Initialize thread based on configuration
        self._initialize_thread()
        
        self.logger.info("GPTThreadManager initialized successfully.")
    
    def _initialize_thread(self):
        """Initialize thread based on configuration settings."""
        try:
            always_create_new = self.openai_config.get('always_create_new_thread', True)
            
            if always_create_new:
                self.logger.info("Creating new thread as configured")
                self._create_new_thread()
            else:
                thread_id = self.openai_config.get('thread_id')
                if thread_id:
                    self.logger.info(f"Attempting to load existing thread: {thread_id}")
                    self._load_existing_thread(thread_id)
                else:
                    self.logger.warning("No thread_id configured and always_create_new_thread is False. Creating new thread.")
                    self._create_new_thread()
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize thread: {e}")
            # Try to create a new thread as fallback
            try:
                self.logger.info("Attempting to create new thread as fallback")
                self._create_new_thread()
            except Exception as fallback_error:
                self.logger.error(f"Failed to create fallback thread: {fallback_error}")
                raise
    
    def _create_new_thread(self):
        """Create a new thread."""
        try:
            thread = self.client.beta.threads.create()
            self.thread_id = thread.id
            self.logger.info(f"Created new thread: {self.thread_id}")
            
            # Update only the thread ID field
            self.config_manager.set('gpt_thread_id', self.thread_id)
            self.config_manager.save_config()
            
        except Exception as e:
            self.logger.error(f"Failed to create new thread: {e}")
            raise
    
    def _load_existing_thread(self, thread_id: str):
        """Load an existing thread by ID."""
        try:
            # Verify thread exists by attempting to retrieve it
            thread = self.client.beta.threads.retrieve(thread_id)
            self.thread_id = thread.id
            self.logger.info(f"Loaded existing thread: {self.thread_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to load existing thread {thread_id}: {e}")
            # Fall back to creating new thread
            self.logger.info("Falling back to creating new thread")
            self._create_new_thread()
    
    def upload_files(self, file_paths: List[str]) -> List[str]:
        """
        Upload files to the assistant for context.
        
        Args:
            file_paths: List of file paths to upload
            
        Returns:
            List of file IDs that were uploaded successfully
        """
        if not self.assistant_id:
            self.logger.error("No assistant_id configured. Cannot upload files.")
            return []
        
        uploaded_file_ids = []
        
        try:
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    self.logger.warning(f"File not found: {file_path}")
                    continue
                
                try:
                    with open(file_path, 'rb') as file:
                        file_obj = self.client.files.create(
                            file=file,
                            purpose='assistants'
                        )
                    
                    # Attach file to assistant
                    self.client.beta.assistants.files.create(
                        assistant_id=self.assistant_id,
                        file_id=file_obj.id
                    )
                    
                    uploaded_file_ids.append(file_obj.id)
                    self.logger.info(f"Successfully uploaded file: {file_path} (ID: {file_obj.id})")
                    
                except Exception as e:
                    self.logger.error(f"Failed to upload file {file_path}: {e}")
            
            return uploaded_file_ids
            
        except Exception as e:
            self.logger.error(f"Error during file upload process: {e}")
            return uploaded_file_ids
    
    def prompt(self, message: str, role: str = "user", additional_files: Optional[List[str]] = None) -> Optional[str]:
        """
        Send a prompt to the assistant and get a response.
        
        Args:
            message: The message to send
            role: Role of the message ("user" or "system")
            additional_files: Optional list of additional file paths to upload before prompting
            
        Returns:
            The assistant's response, or None if failed
        """
        try:
            if not self.thread_id:
                self.logger.error("No thread available for prompting")
                return None
            
            self.logger.info(f"Sending prompt to GPT (role: {role}): {message}")
            
            # Upload additional files if provided
            if additional_files:
                self.logger.info(f"Uploading {len(additional_files)} additional files")
                self.upload_files(additional_files)
            
            # Add message to thread
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role=role,
                content=message
            )
            self.logger.info("Message added to thread successfully.")
            
            if not self.assistant_id:
                self.logger.error("No assistant_id configured. Cannot run assistant.")
                return None
            
            # Run the assistant
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id
            )
            
            if run.status == 'completed':
                self.logger.info("Assistant run completed successfully.")
                
                # Retrieve responses
                messages = self.client.beta.threads.messages.list(
                    thread_id=self.thread_id
                )
                self.logger.info("Retrieved all responses from GPT successfully.")
                
                # Extract only assistant responses
                responses = [msg.content[0].text.value for msg in messages if msg.role == "assistant"]
                if responses:
                    self.logger.info(f"Most recent response: {responses[0]}")
                    return responses[0]  # Return the most recent response
                else:
                    self.logger.warning("No assistant responses found.")
                    return None
            else:
                self.logger.error(f"Assistant run failed with status: {run.status}")
                if hasattr(run, 'last_error') and run.last_error:
                    self.logger.error(f"Error details: {run.last_error.message}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error during GPT prompt: {e}")
            raise
    

    
    def get_thread_info(self) -> Dict[str, Any]:
        """Get information about the current thread."""
        return {
            'thread_id': self.thread_id,
            'assistant_id': self.assistant_id,
            'assistant_configured': bool(self.assistant_id)
        }
    
    def cleanup_files(self, file_ids: List[str]):
        """
        Clean up uploaded files.
        
        Args:
            file_ids: List of file IDs to delete
        """
        try:
            for file_id in file_ids:
                try:
                    self.client.files.delete(file_id)
                    self.logger.info(f"Deleted file: {file_id}")
                except Exception as e:
                    self.logger.error(f"Failed to delete file {file_id}: {e}")
        except Exception as e:
            self.logger.error(f"Error during file cleanup: {e}")


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='GPT Thread Manager - Generic interface to GPT assistant')
    parser.add_argument('--config', '-c', 
                       default='autopost_config.enhanced.json',
                       help='Path to configuration file (default: autopost_config.enhanced.json)')
    parser.add_argument('--prompt', '-p',
                       help='Prompt text to send to the assistant')
    
    args = parser.parse_args()
    
    try:
        # Initialize the thread manager with specified config
        print(f"Initializing GPTThreadManager with config: {args.config}")
        manager = GPTThreadManager(args.config)
        
        # Display thread info
        thread_info = manager.get_thread_info()
        print(f"Thread ID: {thread_info['thread_id']}")
        print(f"Assistant ID: {thread_info['assistant_id']}")
        print(f"Assistant configured: {thread_info['assistant_configured']}")
        
        # Send prompt if provided
        if args.prompt:
            print(f"\nSending prompt: {args.prompt}")
            response = manager.prompt(args.prompt)
            if response:
                print(f"\nResponse:\n{response}")
            else:
                print("\nNo response received (check if assistant_id is configured)")
        else:
            # Default test prompt if no prompt provided
            print("\nSending default test prompt...")
            response = manager.prompt("Hello! Can you help me with content generation?")
            if response:
                print(f"\nResponse:\n{response}")
            else:
                print("\nNo response received (check if assistant_id is configured)")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
