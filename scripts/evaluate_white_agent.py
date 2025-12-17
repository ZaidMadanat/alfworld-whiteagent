import argparse
import csv
import time
from white_agent.agent import WhiteAgent

class MockGreenAgent:
    """
    A mock Green Agent that acts as the Assessor.
    In a real scenario, this would be the actual Green Agent or connect to it.
    For this white agent repo, we simulate the environment/assessor role.
    """
    def __init__(self):
        self.tasks = [
            {"obs": "You are in a kitchen. There is an apple on the table.", "goal": "put apple in fridge"},
            {"obs": "You are in a living room. A lamp is off.", "goal": "turn on lamp"}
        ]

    def get_task(self, idx):
        if idx < len(self.tasks):
            return self.tasks[idx]
        return None

    def assess(self, action, goal):
        # valid actions mock
        if "look" in action:
            return "You see more things.", 0.0, False
        if "inventory" in action:
            return "You are carrying nothing.", 0.0, False
        
        # simplified goal check
        if "process" in goal or "do" in action: # very dumb check
            return "Task completed.", 1.0, True
        
        return "Nothing happened.", 0.0, False

def evaluate(episodes=5, output_file="scores.csv"):
    white_agent = WhiteAgent()
    green_agent = MockGreenAgent()
    
    results = []
    
    print(f"Starting evaluation of {episodes} episodes...")
    
    for i in range(episodes):
        task = green_agent.get_task(i % 2)
        obs = task["obs"]
        goal = task["goal"]
        full_obs = f"Goal: {goal}. {obs}"
        
        print(f"Episode {i+1}: {goal}")
        
        current_obs = white_agent.reset(full_obs)
        done = False
        step = 0
        max_steps = 10
        total_reward = 0.0
        
        while not done and step < max_steps:
            action = white_agent.act(current_obs)
            print(f"  Step {step}: Action={action}")
            
            next_obs, reward, done_flag = green_agent.assess(action, goal)
            # Force done if max steps reached
            if step == max_steps - 1:
                done_flag = True
                
            white_agent.observe(action, reward, done_flag, {})
            current_obs = next_obs
            total_reward += reward
            step += 1
            done = done_flag
        
        print(f"  Result: Reward={total_reward}, Steps={step}")
        results.append({"episode": i, "reward": total_reward, "steps": step, "goal": goal})

    # Save scores
    with open(output_file, "w", newline="") as csvfile:
        fieldnames = ["episode", "goal", "reward", "steps"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
            
    print(f"Evaluation complete. Scores saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--output", type=str, default="evaluation_scores.csv")
    args = parser.parse_args()
    
    evaluate(args.episodes, args.output)
