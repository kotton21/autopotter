import openai
import json

class GPTAssistant:
    def __init__(self, config_path="config_gpt.json"):
        with open(config_path, "r") as f:
            self.config = json.load(f)
        
        self.client = openai.OpenAI(api_key=self.config["API_KEY"])

    def prompt(self, message, role="user"):
        # Step 1: Add a message to the thread
        self.client.beta.threads.messages.create(
            thread_id=self.config["THREAD_ID"],
            role=role,
            content=message
        )

        # Step 2: Run the assistant
        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=self.config["THREAD_ID"],
            assistant_id=self.config["ASSISTANT_ID"]
        )
        
        assert run.status == 'completed'

        # Step 3: Retrieve responses
        messages = self.client.beta.threads.messages.list(
            thread_id=self.config["THREAD_ID"]
        )
        
        # Step 4: Extract only assistant responses
        responses = [msg.content[0].text.value for msg in messages if msg.role == "assistant"]
        for response in responses:
            print(response)
        
        return responses


if __name__ == "__main__":
    assistant = GPTAssistant()
    user_input = input("Enter your message: ")
    assistant.prompt(user_input)
