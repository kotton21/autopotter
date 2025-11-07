import openai
from typing import Optional, Any
from autopotter_tools.logger import get_logger


class GPTAPI:
    """
    Simple wrapper for OpenAI GPT Responses API.
    Handles API access verification and provides a clean interface for sending prompts.

    """
    
    def __init__(self, model: str, use_previous_response_id: bool = False, previous_response_id: Optional[str] = None):
        """
        Initialize the GPT API client.
        
        Args:
            use_previous_response_id: Whether to save previous_response_id from responses
            previous_response_id: Optional previous response ID to pass to API calls
        """
        self.logger = get_logger('gpt_api')
        self.model = model
        self.use_previous_response_id = use_previous_response_id
        self.previous_response_id = previous_response_id
        
        self.logger.info("Initializing GPT API client...")
        
        # Initialize OpenAI client
        try:
            self.client = openai.OpenAI()
            self.logger.info("OpenAI client created")
        except Exception as e:
            self.logger.error(f"Failed to create OpenAI client: {e}")
            raise
        
        # Check API access
        self._check_access()
        
        self.logger.info("GPT API initialized successfully")
        if self.use_previous_response_id:
            self.logger.info(f"Previous response ID tracking enabled: {self.previous_response_id}")
    
    def _check_access(self):
        """
        Verify that we have valid API access by attempting a simple API call.
        Raises an error if access is not available.
        """
        try:
            self.logger.info("Checking API access...")
            # Try to list models as a simple access check
            # This is a lightweight operation that verifies API key validity
            models = self.client.models.list()
            self.logger.info("API access verified successfully")
        except openai.AuthenticationError as e:
            self.logger.error(f"Authentication failed: {e}")
            raise ValueError(f"OpenAI API authentication failed: {e}")
        except openai.PermissionDeniedError as e:
            self.logger.error(f"Permission denied: {e}")
            raise ValueError(f"OpenAI API permission denied: {e}")
        except openai.RateLimitError as e:
            self.logger.error(f"Rate limit exceeded: {e}")
            raise ValueError(f"OpenAI API rate limit exceeded: {e}")
        except openai.ServiceUnavailableError as e:
            self.logger.error(f"Service unavailable: {e}")
            raise ValueError(f"OpenAI API service unavailable: {e}")
        except openai.APIError as e:
            self.logger.error(f"API error: {e}")
            raise ValueError(f"OpenAI API error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected Error durning API access check: {e}")
            raise ValueError(f"Unexpected Error during API access check: {e}")
    
    def prompt(
        self,
        user_instructions: Optional[str] = "hello world",
        developer_instructions: Optional[str] = None,
        text_format: Optional[Any] = None
    ):
        """
        Send a prompt to the GPT API and return the response.
        
        Args:
            prompt: The main user prompt
            text_format: Optional Pydantic model or format for structured output
            developer_instructions: Optional developer/system instructions
            user_instructions: Optional additional user instructions (appended to prompt)
            
        Returns:
            The API response object
        """
        self.logger.info(f"Sending prompt to model: {self.model}")
        
        try:
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "input": [
                    {"role": "user", "content": user_instructions}
                ]
            }
            self.logger.debug("Added user instructions")
            
            if developer_instructions:
                api_params["input"].append({"role": "developer", "content": developer_instructions})
                self.logger.debug("Added developer instructions")
            
            
            # Add text_format if provided
            if text_format:
                api_params["text_format"] = text_format
                self.logger.debug("Using structured output format")
            
            # Add previous_response_id if available
            if self.use_previous_response_id and self.previous_response_id:
                api_params["previous_response_id"] = self.previous_response_id
                self.logger.debug(f"Using previous response ID: {self.previous_response_id}")
            
            # Make API call
            self.logger.debug("Calling responses.parse API...")
            response = self.client.responses.parse(**api_params)

            # print("\n\n")
            # print(response)
            # print("\n\n")
            
            # Check for errors early in response
            if response is None:
                self.logger.error("API response is None.")
                raise RuntimeError("API response is None.")
            
            # Check for error field in response
            if hasattr(response, 'error') and response.error is not None:
                error_msg = f"API response contains error: {response.error}"
                self.logger.error(error_msg)
                # raise RuntimeError(error_msg)
            
            # Check response status
            if hasattr(response, 'status'):
                if response.status != 'completed':
                    status_msg = f"API response status is '{response.status}' (expected 'completed')"
                    if hasattr(response, 'incomplete_details') and response.incomplete_details:
                        status_msg += f" - Details: {response.incomplete_details}"
                    self.logger.warning(status_msg)

            # ensure response contains a parsed output when using text_format
            if text_format:
                if not hasattr(response, "output_parsed"):
                    self.logger.error("API response must contain a parsed output when using text_format.")
                    raise RuntimeError("API response must contain a parsed output when using text_format.")
            
            # ensure response contains a message/content item when not using text_format
            else:
                # The response may have reasoning items first, so we need to find the message item
                if not hasattr(response, "output") or response.output is None or len(response.output) == 0:
                    self.logger.error("API response is empty or missing output.")
                    raise RuntimeError("API response is empty or missing output.")
                
                # Find the message item (may not be at index 0 if there's a reasoning item)
                for item in response.output:
                    # check for type='message' attribute
                    if hasattr(item, "type") and item.type == "message":
                        if hasattr(item, "content") and item.content is not None and len(item.content) > 0:
                            ret = item

                if ret is None:
                    self.logger.error("API response does not contain a message item with content.")
                    raise RuntimeError("API response does not contain a message item with content.")
                    
            # Log token usage information
            if hasattr(response, 'usage') and response.usage:
                total_tokens = getattr(response.usage, 'total_tokens', None)
                input_tokens = getattr(response.usage, 'input_tokens', None)
                output_tokens = getattr(response.usage, 'output_tokens', None)
                cached_tokens = getattr(response.usage.input_tokens_details, 'cached_tokens', None)
                reasoning_tokens = getattr(response.usage.output_tokens_details, 'reasoning_tokens', None)
                # max_output_tokens = getattr(response, 'max_output_tokens', None)
                
                self.logger.info(f"Tokens Used - Total: {total_tokens}, Input: {input_tokens} ({cached_tokens} cached), Output: {output_tokens} ({reasoning_tokens} reasoning)")

            else:
                self.logger.warning("Token usage information not available in response")
            
            # Save response ID if configured
            if self.use_previous_response_id and hasattr(response, 'id'):
                self.previous_response_id = response.id
                self.logger.info(f"Saved previous response ID: {response.id}")
            
            self.logger.info("API call completed successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Error during API call: {e}")
            raise
    