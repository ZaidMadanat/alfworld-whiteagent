import os
import toml
from openai import OpenAI

class WhiteAgent:
    def __init__(self, config_path="white_agent/config.toml", card_path="agents/white_agent_card.toml"):
        self.config = toml.load(config_path)
        self.card = toml.load(card_path)
        self.system_prompt = self.card.get("description", "You are an ALFWorld agent.")
        
        # Initialize OpenAI client
        # Relies on OPENAI_API_KEY environment variable
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = self.config["agent"].get("model", "gpt-4o")
        
        self.state = {"history": []}

    def reset(self, env_info):
        """
        Resets the agent with the initial environment info.
        """
        self.state = {"step": 0, "history": []}
        
        # Initial observation
        observation = env_info if isinstance(env_info, str) else env_info.get("obs", "")
        
        # Add system prompt and initial observation to history
        self.state["history"].append({"role": "system", "content": self.system_prompt})
        self.state["history"].append({"role": "user", "content": f"Observation: {observation}"})
        
        return observation

    def act(self, observation):
        """
        Decides an action based on the observation using LLM.
        """
        # Append new observation if it's not the very first one (which is done in reset)
        # However, act is called after reset usually.
        # If the history last item was assistant (action), then this observation is new.
        if self.state["history"][-1]["role"] == "assistant":
            self.state["history"].append({"role": "user", "content": f"Observation: {observation}"})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.state["history"],
                temperature=0.0
            )
            content = response.choices[0].message.content.strip()
            
            # Simple parsing: separate thought from action if present
            # Assuming format "> think: ... \n command"
            if "> think:" in content:
                parts = content.split("\n")
                # Filter out lines starting with "> think:" or empty lines
                action_lines = [line.strip() for line in parts if not line.strip().startswith("> think:") and line.strip()]
                if action_lines:
                    action = action_lines[-1] # Take the last non-empty line as the command
                else:
                    action = "look" # Fallback
            else:
                action = content
                
        except Exception as e:
            # Fallback if API fails
            print(f"Error calling LLM: {e}")
            action = "look"

        self.state["history"].append({"role": "assistant", "content": content}) # Log full content including thought
        return action

    def observe(self, action, reward, done, info):
        """
        Updates the agent's internal state.
        """
        self.state["step"] += 1
        self.state["last_reward"] = reward
        self.state["done"] = done
        # The observation for the *next* step will be passed to act() or the next history update.
        # We can optionally log the reward/done status to the history if we want the LLM to know.
        if done:
             self.state["history"].append({"role": "user", "content": f"Episode finished. Reward: {reward}"})

