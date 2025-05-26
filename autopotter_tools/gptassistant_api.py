import openai
import json
from datetime import datetime

class GPTAssistant:
    def __init__(self, config_path="config_gpt.json", log_file=None):
        self.log_file = log_file
        self.log_message("Initializing GPTAssistant...")
        
        with open(config_path, "r") as f:
            self.config = json.load(f)
        
        self.client = openai.OpenAI(api_key=self.config["API_KEY"])
        self.log_message("GPTAssistant initialized successfully.")


    def prompt(self, message, role="user"):
        try:
            self.log_message(f"Sending prompt to GPT: {message}")
            
            # Step 1: Add a message to the thread
            self.client.beta.threads.messages.create(
                thread_id=self.config["THREAD_ID"],
                role=role,
                content=message
            )
            self.log_message("Message added to thread successfully.")

            # Step 2: Run the assistant
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=self.config["THREAD_ID"],
                assistant_id=self.config["ASSISTANT_ID"]
            )
            
            if run.status == 'completed':
                self.log_message("Assistant run completed successfully.")

                # Step 3: Retrieve responses
                messages = self.client.beta.threads.messages.list(
                    thread_id=self.config["THREAD_ID"]
                )
                self.log_message("Retrieved all responses from GPT successfully.")

                
                # Step 4: Extract only assistant responses
                responses = [msg.content[0].text.value for msg in messages if msg.role == "assistant"]
                if responses:
                    self.log_message(f"Most recent response: {responses[0]}")
                    return responses[0]  # Return the most recent response
                else:
                    self.log_message("No assistant responses found.")
                    return None
            else:
                self.log_message(f"Assistant run failed with status: {run.status}")
                self.log_message(run.last_error.message if run.last_error else str(run))
        
        except Exception as e:
            self.log_message(f"Error during GPT prompt: {e}")
            raise

    def log_message(self, message):
        """Log a message to the log file with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] GPTAssistant: {message}"
        if self.log_file is None:
            print(msg)
        else:
            with open(self.log_file, "a") as f:
                f.write(msg+"\n")

        
if __name__ == "__main__":
    assistant = GPTAssistant()
    user_input = input("Enter your message: ")
    assistant.prompt(user_input)
