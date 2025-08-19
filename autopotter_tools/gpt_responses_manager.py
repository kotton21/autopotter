import openai
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports when running as script
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .logger import get_logger
except ImportError:
    from logger import get_logger

class GPTResponsesManager:
    """
    Direct interface to GPT using the Responses API (Chat Completions).
    Replaces the Assistants API with simpler, more direct chat completions.
    Handles context management, content generation, and conversation history.
    """
    
    def __init__(self, config_path: str = "autopost_config.enhanced.json"):
        self.logger = get_logger('gpt_responses_manager')
        self.logger.info("Initializing GPTResponsesManager...")
        
        # Load configuration using the new config system
        from config import get_config
        self.config_manager = get_config(config_path)
        self.openai_config = self.config_manager.get_openai_config()
        
        # Validate required configuration
        if not self.openai_config.get('api_key'):
            raise ValueError("OpenAI API key is required")
        
        if not self.openai_config.get('model'):
            self.logger.warning("No model specified. Using default gpt-4o.")
        
        self.client = openai.OpenAI(api_key=self.openai_config['api_key'])
        self.model = self.openai_config.get('model', 'gpt-4o')
        self.max_tokens = self.openai_config.get('max_tokens', 4000)
        self.temperature = self.openai_config.get('temperature', 0.7)
        
        # Conversation history for context management
        self.conversation_history = []
        self.max_history_length = self.openai_config.get('max_history_length', 10)
        
        # System prompt from configuration
        self.system_prompt = self.openai_config.get('creation_prompt', 
            "You are a creative AI assistant for 3D printing pottery content. You help generate engaging social media content ideas based on available resources and account analytics.")
        
        self.logger.info(f"GPTResponsesManager initialized successfully with model: {self.model}")
    
    def prompt(self, user_prompt: str, context_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Send a prompt to GPT and get a response.
        
        Args:
            user_prompt: The user's prompt/question
            context_data: Optional context data to include (e.g., analytics, inventory)
            
        Returns:
            GPT's response text or None if failed
        """
        try:
            self.logger.info("Preparing prompt for GPT...")
            
            # Build the full prompt with context
            full_prompt = self._build_full_prompt(user_prompt, context_data)
            
            # Prepare messages for the API call
            messages = self._prepare_messages(full_prompt)
            
            self.logger.info("Sending request to GPT...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Extract response content
            response_text = response.choices[0].message.content
            self.logger.info("GPT response received successfully")
            
            # Update conversation history
            self._update_conversation_history(user_prompt, response_text)
            
            return response_text
            
        except Exception as e:
            self.logger.error(f"Error during GPT prompt: {e}")
            raise
    
    def _build_full_prompt(self, user_prompt: str, context_data: Optional[Dict[str, Any]]) -> str:
        """
        Build a comprehensive prompt that includes context data.
        
        Args:
            user_prompt: The user's original prompt
            context_data: Optional context data to include
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = [user_prompt]
        
        if context_data:
            # Add context data as structured information
            context_json = json.dumps(context_data, indent=2)
            prompt_parts.append(f"\nAvailable Resources:\n{context_json}")
        
        return "\n".join(prompt_parts)
    
    def _prepare_messages(self, full_prompt: str) -> List[Dict[str, str]]:
        """
        Prepare the messages array for the Chat Completions API.
        
        Args:
            full_prompt: The complete user prompt
            
        Returns:
            List of message dictionaries
        """
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add conversation history if available
        for msg in self.conversation_history[-self.max_history_length:]:
            messages.append(msg)
        
        # Add current user prompt
        messages.append({"role": "user", "content": full_prompt})
        
        return messages
    
    def _update_conversation_history(self, user_prompt: str, assistant_response: str):
        """
        Update the conversation history for context in future requests.
        
        Args:
            user_prompt: The user's prompt
            assistant_response: The assistant's response
        """
        # Add user message
        self.conversation_history.append({"role": "user", "content": user_prompt})
        
        # Add assistant response
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # Trim history if it exceeds maximum length
        if len(self.conversation_history) > self.max_history_length * 2:  # *2 because each exchange is 2 messages
            self.conversation_history = self.conversation_history[-self.max_history_length * 2:]
        
        self.logger.debug(f"Updated conversation history. Current length: {len(self.conversation_history)}")
    
    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        self.logger.info("Conversation history cleared")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return self.conversation_history.copy()
    
    def set_system_prompt(self, new_prompt: str):
        """
        Update the system prompt used for all requests.
        
        Args:
            new_prompt: New system prompt
        """
        self.system_prompt = new_prompt
        self.logger.info("System prompt updated")
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about the current configuration."""
        return {
            'model': self.model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'max_history_length': self.max_history_length,
            'conversation_history_length': len(self.conversation_history),
            'system_prompt': self.system_prompt[:100] + "..." if len(self.system_prompt) > 100 else self.system_prompt
        }
    
    def update_model_parameters(self, max_tokens: Optional[int] = None, 
                              temperature: Optional[float] = None):
        """
        Update model parameters for future requests.
        
        Args:
            max_tokens: Maximum tokens for responses
            temperature: Creativity level (0.0 to 2.0)
        """
        if max_tokens is not None:
            self.max_tokens = max_tokens
            self.logger.info(f"Updated max_tokens to: {max_tokens}")
        
        if temperature is not None:
            if 0.0 <= temperature <= 2.0:
                self.temperature = temperature
                self.logger.info(f"Updated temperature to: {temperature}")
            else:
                self.logger.warning(f"Invalid temperature value: {temperature}. Must be between 0.0 and 2.0")


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='GPT Responses Manager - Direct interface to GPT using Chat Completions API')
    parser.add_argument('--config', '-c', 
                       default='autopost_config.enhanced.json',
                       help='Path to configuration file (default: autopost_config.enhanced.json)')
    parser.add_argument('--prompt', '-p',
                       help='Prompt text to send to GPT')
    
    args = parser.parse_args()
    
    try:
        # Initialize the responses manager with specified config
        print(f"Initializing GPTResponsesManager with config: {args.config}")
        manager = GPTResponsesManager(args.config)
        
        # Display configuration info
        config_info = manager.get_config_info()
        print(f"Model: {config_info['model']}")
        print(f"Max Tokens: {config_info['max_tokens']}")
        print(f"Temperature: {config_info['temperature']}")
        print(f"System Prompt: {config_info['system_prompt']}")
        
        # Send prompt if provided
        if args.prompt:
            print(f"\nSending prompt: {args.prompt}")
            response = manager.prompt(args.prompt)
            if response:
                print(f"\nResponse:\n{response}")
            else:
                print("\nNo response received")
        else:
            # Default test prompt if no prompt provided
            print("\nSending default test prompt...")
            response = manager.prompt("Hello! Can you help me with content generation?")
            if response:
                print(f"\nResponse:\n{response}")
            else:
                print("\nNo response received")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
