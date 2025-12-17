import os
import toml
from openai import OpenAI


class WhiteAgent:
    def __init__(self, config_path="white_agent/config.toml", card_path="agents/white_agent_card.toml"):
        self.config = toml.load(config_path)
        self.card = toml.load(card_path)
        self.system_prompt = self.card.get("description", "You are an ALFWorld agent.")

        # Agent configuration
        self.policy_type = self.config["agent"].get("policy_type", "neural")
        self.model = self.config["agent"].get("model", "gpt-4o")
        self.max_reflections = self.config["agent"].get("max_reflections", 3)

        # Initialize OpenAI client only if an API key is present
        api_key = os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None

        # Runtime state
        self.state = {}
        self.reflections = []

    def _recent_lessons(self):
        """Return a condensed reflection block for the prompt."""
        if not self.reflections:
            return ""
        return "Recent lessons:\n- " + "\n- ".join(self.reflections[: self.max_reflections])

    def reset(self, env_info):
        """
        Resets the agent with the initial environment info.
        """
        observation = env_info if isinstance(env_info, str) else env_info.get("obs", "")

        history = [{"role": "system", "content": self.system_prompt}]
        lessons = self._recent_lessons()
        if lessons:
            history.append({"role": "system", "content": lessons})
        history.append({"role": "user", "content": f"Observation: {observation}"})

        self.state = {
            "step": 0,
            "history": history,
            "trajectory": [],
            "last_observation": observation,
        }

        return observation

    def _extract_action(self, content: str) -> str:
        """Extract the action line from the LLM response."""
        if "> think:" in content:
            parts = content.split("\n")
            action_lines = [
                line.strip()
                for line in parts
                if not line.strip().startswith("> think:") and line.strip()
            ]
            if action_lines:
                return action_lines[-1]
        return content.strip() or "look"

    def _fallback_action(self, observation: str) -> str:
        """Very small heuristic policy when the LLM call fails or is unavailable."""
        obs = observation.lower()
        if "lamp" in obs and "off" in obs:
            return "turn on lamp"
        if "fridge" in obs and "apple" in obs:
            return "put apple in fridge"
        if "inventory" in obs:
            return "inventory"
        return "look"

    def act(self, observation):
        """
        Decides an action based on the observation using LLM, with a safe fallback.
        """
        self.state["last_observation"] = observation

        # If an assistant message was just added, log the new observation
        history = self.state.get("history", [])
        if history and history[-1]["role"] == "assistant":
            history.append({"role": "user", "content": f"Observation: {observation}"})
        elif not history:
            # If reset was not called, start a minimal history
            history.extend([
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Observation: {observation}"}
            ])
            self.state["step"] = 0
        self.state["history"] = history

        content = None
        action = None

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.state["history"],
                    temperature=0.0
                )
                content = response.choices[0].message.content.strip()
                action = self._extract_action(content)
            except Exception as e:
                print(f"Error calling LLM: {e}")
        else:
            # Avoid silent no-op when the API key is missing
            print("OpenAI client not configured; using fallback policy.")

        if not action:
            action = self._fallback_action(observation)
        if not content:
            content = action

        self.state["history"].append({"role": "assistant", "content": content})
        return action

    def _summarize_trajectory(self):
        """Create a short reflection from the last episode trajectory."""
        traj = self.state.get("trajectory", [])
        if not traj:
            return "No trajectory recorded."

        last = traj[-1]
        reward = last.get("reward", 0.0)
        done_flag = last.get("done", False)
        last_action = last.get("action", "unknown")
        last_obs = last.get("observation", "")

        if reward > 0:
            return f"Success pattern: finishing with '{last_action}' after seeing '{last_obs}'."
        if done_flag and reward <= 0:
            return f"Failure to reach goal; last action '{last_action}' after '{last_obs}'. Try alternative paths and diversify exploration."
        return f"Partial progress; last action '{last_action}'. Keep exploring and avoid repeating ineffective commands."

    def _add_reflection(self, reflection: str):
        """Push a new reflection and keep only the most recent ones."""
        if reflection:
            self.reflections.insert(0, reflection)
            if len(self.reflections) > self.max_reflections:
                self.reflections = self.reflections[: self.max_reflections]

    def observe(self, action, reward, done, info):
        """
        Updates the agent's internal state.
        """
        self.state["step"] = self.state.get("step", 0) + 1
        self.state["last_reward"] = reward
        self.state["done"] = done
        self.state.setdefault("trajectory", []).append(
            {
                "observation": self.state.get("last_observation", ""),
                "action": action,
                "reward": reward,
                "done": done,
                "feedback": info.get("feedback") if isinstance(info, dict) else None,
            }
        )
        if done:
            reflection = self._summarize_trajectory()
            self._add_reflection(reflection)
            end_msg = f"Episode finished. Reward: {reward}."
            if isinstance(info, dict) and info.get("feedback"):
                end_msg += f" Evaluator feedback: {info['feedback']}"
            self.state.setdefault("history", []).append({"role": "user", "content": end_msg})
            self.state["history"].append({"role": "system", "content": f"Lesson learned: {reflection}"})
