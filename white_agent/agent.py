import os
import re
import toml
from openai import OpenAI


class WhiteAgent:
    """
    ALFWorld White Agent with reflection-augmented GPT-4o policy.
    
    Architecture (per step):
    Observation → GPT-4o policy call → action extraction → environment step 
    → store transition → end-of-episode reflection
    
    Features:
    - Structured workflow: Understand → Explore → Interact → Manipulate → Complete
    - Multi-objective behavior: Task completion + cleanup awareness
    - Cross-episode reflection with behavior-focused lessons
    - Repetition detection to avoid consecutive identical actions
    """

    # Valid ALFWorld action patterns
    VALID_ACTIONS = [
        r"^go to .+$",
        r"^take .+ from .+$",
        r"^put .+ in/on .+$",
        r"^put .+ in .+$",
        r"^put .+ on .+$",
        r"^open .+$",
        r"^close .+$",
        r"^toggle .+$",
        r"^heat .+ with .+$",
        r"^cool .+ with .+$",
        r"^clean .+ with .+$",
        r"^use .+$",
        r"^examine .+$",
        r"^look$",
        r"^inventory$",
        r"^turn on .+$",
        r"^turn off .+$",
    ]

    def __init__(self, config_path="white_agent/config.toml", card_path="agents/white_agent_card.toml"):
        self.config = toml.load(config_path)
        self.card = toml.load(card_path)
        self.system_prompt = self.card.get("description", "You are an ALFWorld agent.")

        # Agent configuration
        self.policy_type = self.config["agent"].get("policy_type", "neural")
        self.model = self.config["agent"].get("model", "gpt-4o")
        self.max_reflections = self.config["agent"].get("max_reflections", 3)
        self.max_steps = self.config.get("evaluation", {}).get("max_steps", 50)
        self.track_cleanup = self.config["agent"].get("track_cleanup", True)

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
        lessons = self.reflections[: self.max_reflections]
        return "Recent lessons from past episodes:\n- " + "\n- ".join(lessons)

    def _build_system_prompt(self):
        """Build the full system prompt with reflection lessons."""
        base_prompt = self.system_prompt
        lessons = self._recent_lessons()
        if lessons:
            return f"{base_prompt}\n\n---\n{lessons}"
        return base_prompt

    def reset(self, env_info):
        """
        Resets the agent with the initial environment info.
        """
        observation = env_info if isinstance(env_info, str) else env_info.get("obs", "")

        history = [{"role": "system", "content": self._build_system_prompt()}]
        history.append({"role": "user", "content": f"Observation: {observation}"})

        self.state = {
            "step": 0,
            "history": history,
            "trajectory": [],
            "last_observation": observation,
            "last_action": None,
            "opened_containers": set(),  # Track containers opened during episode
            "closed_containers": set(),  # Track containers closed during episode
            "action_sequence": [],  # For cycle detection
        }

        return observation

    def _is_valid_action(self, action: str) -> bool:
        """Check if the action matches valid ALFWorld command patterns."""
        action_lower = action.lower().strip()
        for pattern in self.VALID_ACTIONS:
            if re.match(pattern, action_lower):
                return True
        return False

    def _extract_action(self, content: str) -> str:
        """
        Extract the action line from the LLM response.
        Strips any reasoning (> think: ...) and returns a clean command.
        """
        if not content:
            return "look"

        lines = content.strip().split("\n")
        action_lines = []

        for line in lines:
            line = line.strip()
            # Skip thinking lines
            if line.startswith("> think:") or line.startswith(">think:"):
                continue
            # Skip empty lines
            if not line:
                continue
            action_lines.append(line)

        if not action_lines:
            return "look"

        # Take the last non-thinking line as the action
        candidate = action_lines[-1]

        # Clean up common LLM artifacts
        candidate = candidate.strip('"\'`')
        candidate = re.sub(r'^(action:|Action:|ACTION:)\s*', '', candidate)

        # Validate it's a proper ALFWorld command
        if self._is_valid_action(candidate):
            return candidate

        # If not valid, try to find a valid action in any line
        for line in reversed(action_lines):
            cleaned = line.strip('"\'`')
            cleaned = re.sub(r'^(action:|Action:|ACTION:)\s*', '', cleaned)
            if self._is_valid_action(cleaned):
                return cleaned

        # Default fallback
        return candidate if candidate else "look"

    def _detect_repetition(self, action: str) -> bool:
        """Detect if the current action is a repetition of the last action."""
        last = self.state.get("last_action")
        if last and action.lower().strip() == last.lower().strip():
            return True
        return False

    def _detect_cycle(self, action: str, window: int = 4) -> bool:
        """Detect if the agent is stuck in a short navigation loop (A→B→A→B)."""
        seq = self.state.get("action_sequence", [])
        if len(seq) < window - 1:  # Need at least 3 previous actions + 1 new
            return False

        recent = seq[-(window - 1):] + [action]
        # Check for A→B→A→B pattern
        if len(recent) >= 4:
            if recent[-1] == recent[-3] and recent[-2] == recent[-4]:
                return True
        return False

    def _track_container(self, action: str, observation: str):
        """Track container open/close actions for cleanup scoring."""
        action_lower = action.lower()

        # Track opened containers
        if action_lower.startswith("open "):
            container = action_lower.replace("open ", "").strip()
            self.state["opened_containers"].add(container)

        # Track closed containers
        if action_lower.startswith("close "):
            container = action_lower.replace("close ", "").strip()
            self.state["closed_containers"].add(container)

    def _calculate_cleanup_score(self) -> float:
        """Calculate cleanup score: proportion of opened containers that were closed."""
        opened = self.state.get("opened_containers", set())
        closed = self.state.get("closed_containers", set())

        if not opened:
            return 1.0  # 100% if no containers were opened

        closed_that_were_opened = opened.intersection(closed)
        return len(closed_that_were_opened) / len(opened)

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
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": f"Observation: {observation}"}
            ])
            self.state["step"] = 0
        self.state["history"] = history

        content = None
        action = None

        if self.client:
            try:
                # Add repetition warning if needed
                messages = list(self.state["history"])
                last_action = self.state.get("last_action")
                if last_action:
                    warning = f"[Note: Avoid repeating '{last_action}' if it didn't work.]"
                    if messages and messages[-1]["role"] == "user":
                        messages[-1] = {
                            "role": "user",
                            "content": messages[-1]["content"] + f"\n{warning}"
                        }

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.0
                )
                content = response.choices[0].message.content.strip()
                action = self._extract_action(content)

                # If action is a repeat, try to modify behavior
                if self._detect_repetition(action):
                    # Add stronger warning and retry once
                    retry_msg = messages + [{
                        "role": "user",
                        "content": f"You just did '{action}' and it didn't help. Try a DIFFERENT action."
                    }]
                    retry_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=retry_msg,
                        temperature=0.2  # Slight randomness to break pattern
                    )
                    retry_content = retry_response.choices[0].message.content.strip()
                    retry_action = self._extract_action(retry_content)
                    if retry_action != action:
                        action = retry_action
                        content = retry_content

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
        self.state["last_action"] = action
        self.state.setdefault("action_sequence", []).append(action)

        return action

    def _summarize_trajectory(self):
        """
        Create a behavior-focused reflection from the last episode trajectory.
        Generates specific, transferable lessons rather than generic summaries.
        """
        traj = self.state.get("trajectory", [])
        if not traj:
            return "No trajectory recorded."

        last = traj[-1]
        reward = last.get("reward", 0.0)
        done_flag = last.get("done", False)

        lessons = []

        # Cleanup lesson
        cleanup_score = self._calculate_cleanup_score()
        if cleanup_score < 1.0:
            lessons.append("Always close containers/appliances after use.")

        # Check for repetition patterns
        actions = [t.get("action", "") for t in traj]
        action_counts = {}
        for a in actions:
            action_counts[a] = action_counts.get(a, 0) + 1

        repeated = [a for a, c in action_counts.items() if c >= 3]
        if repeated:
            lessons.append(f"Avoid repeating actions like '{repeated[0]}' excessively.")

        # Check for navigation cycles
        for i in range(len(actions) - 3):
            if actions[i] == actions[i + 2] and actions[i + 1] == actions[i + 3]:
                lessons.append("Avoid navigation loops (going back and forth).")
                break

        # Success/failure specific lessons
        if reward > 0:
            last_action = last.get("action", "unknown")
            lessons.append(f"Success: completed with '{last_action}'.")
        elif done_flag:
            # Analyze why it failed
            last_obs = last.get("observation", "")
            if "clean" in last_obs.lower() or "dirty" in last_obs.lower():
                lessons.append("Verify object state (clean/dirty) before placing.")
            elif "hot" in last_obs.lower() or "cold" in last_obs.lower():
                lessons.append("Verify temperature state before placing.")
            else:
                lessons.append("Try alternative exploration paths when stuck.")

        if not lessons:
            lessons.append("Continue systematic exploration.")

        return " ".join(lessons[:2])  # Keep lessons concise

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

        # Track containers for cleanup scoring
        if self.track_cleanup:
            self._track_container(action, self.state.get("last_observation", ""))

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

            # Build end-of-episode message
            cleanup_score = self._calculate_cleanup_score()
            end_msg = f"Episode finished. Reward: {reward}. Cleanup score: {cleanup_score:.0%}."
            if isinstance(info, dict) and info.get("feedback"):
                end_msg += f" Evaluator feedback: {info['feedback']}"

            self.state.setdefault("history", []).append({"role": "user", "content": end_msg})
            self.state["history"].append({"role": "system", "content": f"Lesson learned: {reflection}"})

    def get_episode_stats(self):
        """Return episode statistics for evaluation."""
        return {
            "steps": self.state.get("step", 0),
            "reward": self.state.get("last_reward", 0.0),
            "cleanup_score": self._calculate_cleanup_score(),
            "trajectory_length": len(self.state.get("trajectory", [])),
            "reflections_count": len(self.reflections),
        }
