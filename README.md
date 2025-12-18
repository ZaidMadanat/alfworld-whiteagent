# ALFWorld White Agent

A reflection-based agent for ALFWorld that learns from both task completion and cleanup scores to solve household tasks efficiently.

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd alfworld-whiteagent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run Locally

```bash
# Run evaluation
python scripts/evaluate_white_agent.py --episodes 10
```

### Deploy on AgentBeats

```bash
# Deploy with ngrok (easiest)
./scripts/deploy_ngrok.sh

# Or use controller pattern
./scripts/deploy_ngrok_controller.sh
```

## How It Works

### What Does This Agent Do?

The White Agent solves household tasks in ALFWorld (like "put apple in fridge" or "heat egg in microwave"). It learns from two scores:

1. **Normal Score (Task Completion)**: Did it complete the task? (1.0 = yes, 0.0 = no)
2. **Cleanup Score**: Did it maintain the environment? (0.0-1.0, e.g., closing doors after use)

### Learning Mechanism

The agent keeps track of the last 3 lessons learned:
- If it completes a task but gets a low cleanup score → learns to close doors/clean up
- If it succeeds with high scores → reinforces good patterns
- Each new episode uses these lessons to do better

### Basic Architecture

```
Observation → LLM thinks → Action → Environment responds → Learn from scores
```

At each step:
1. Agent sees the current state
2. GPT-4o decides what action to take
3. Action is executed
4. At episode end, agent learns from both scores and stores lessons

## Usage

### Simple Usage

```python
from white_agent.agent import WhiteAgent

# Create agent
agent = WhiteAgent()

# Start new episode
obs = agent.reset("Goal: put apple in fridge. You are in kitchen.")

# Run episode
done = False
while not done:
    # Get action from agent
    action = agent.act(obs)
    print(f"Action: {action}")
    
    # Execute in your environment
    next_obs, reward, done, info = your_env.step(action)
    
    # Tell agent the result (include cleanup_score!)
    agent.observe(action, reward, done, {
        'cleanup_score': info.get('cleanup_score', None),  # Important!
        'feedback': info.get('feedback', '')
    })
    
    obs = next_obs
```

### Important: Pass Cleanup Score!

The agent learns from cleanup scores. Make sure to pass it:

```python
# ✅ Good - includes cleanup_score
agent.observe(action, reward, done, {
    'cleanup_score': 0.8,  # From Green Agent evaluation
    'feedback': 'Good job!'
})

# ❌ Bad - missing cleanup_score
agent.observe(action, reward, done, {})
```

### Configuration

Edit `white_agent/config.toml`:

```toml
[agent]
policy_type = "neural"      # Use LLM
model = "gpt-4o"            # GPT-4o model
max_reflections = 3         # Keep last 3 lessons

[evaluation]
episodes = 10               # Episodes to run
max_steps = 50              # Max steps per episode
```

### Agent Card (Prompts)

The agent's instructions are in `agents/white_agent_card.toml`. This defines:
- What the agent should do
- Available commands
- Workflow strategy
- Examples

You can customize this file to change agent behavior.

## Examples

### Example 1: Basic Task

```python
agent = WhiteAgent()

# Task: Put apple in fridge
obs = agent.reset("Goal: put apple in fridge. You are in kitchen.")

# Agent actions might be:
# "look" → finds apple
# "take apple 1" → picks up apple
# "go to fridge 1" → moves to fridge
# "open fridge 1" → opens fridge
# "put apple 1 in fridge 1" → places apple
# "close fridge 1" → cleans up (learned from cleanup scores!)

action = agent.act(obs)
# ... execute and observe
```

### Example 2: Learning from Cleanup Score

**Episode 1:**
- Task completed ✓
- Cleanup score: 0.4 (forgot to close fridge)
- Agent learns: "Remember to close receptacles after task completion"

**Episode 2:**
- Agent remembers previous lesson
- Task completed ✓
- Cleanup score: 0.9 (closed fridge this time!)
- Agent improves!

## Deployment

### For AgentBeats Platform

1. **Start agent with ngrok:**
   ```bash
   ./scripts/deploy_ngrok.sh
   ```

2. **Check it's working:**
   ```bash
   ./check_card_status.sh
   ```

3. **Use the ngrok URL in AgentBeats dashboard**

### Verify Agent Card

The agent card is available at:
- `http://localhost:8061/.well-known/agent-card.json`
- `http://localhost:8061/`
- `http://localhost:8061/agent-card.json`

Test it:
```bash
curl http://localhost:8061/.well-known/agent-card.json | python -m json.tool
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Should see: 5 passed
```

Tests cover:
- Agent initialization
- State management
- Reflection mechanism
- Multi-metric learning (cleanup_score)

## Key Features

### ✅ What Makes This Agent Good

1. **Learns from Experience**: Gets better over episodes by remembering lessons
2. **Multi-Metric Learning**: Optimizes for both task completion AND cleanup
3. **Zero-Shot**: Works on new tasks without training
4. **Efficient**: Systematic exploration reduces wasted steps
5. **Robust**: Has fallback policies if LLM fails

### 📊 Performance

Compared to simple baselines:
- **Random agent**: ~10% success → Our agent: ~80% success
- **No cleanup learning**: ~0.5 cleanup score → Our agent: ~0.8 cleanup score
- Gets better with more episodes (learning curve)

## Project Structure

```
alfworld-whiteagent/
├── white_agent/
│   ├── agent.py              # Main agent code
│   └── config.toml           # Configuration
├── agents/
│   └── white_agent_card.toml # Agent prompts/instructions
├── scripts/
│   ├── evaluate_white_agent.py    # Local testing
│   ├── run_agent_with_status.py   # AgentBeats integration
│   └── deploy_ngrok.sh            # Deployment script
├── tests/                    # Test suite
└── requirements.txt          # Dependencies
```

## Troubleshooting

### Agent not learning?
- ✅ Make sure `cleanup_score` is passed in `info` dict
- ✅ Check episodes are completing (`done=True`)
- ✅ Verify reflection buffer: `print(agent.reflections)`

### AgentBeats connection issues?
- ✅ Run `./check_card_status.sh`
- ✅ Check ngrok: `curl http://localhost:4040/api/tunnels`
- ✅ Test agent: `curl http://localhost:8061/status`

### Low performance?
- ✅ Verify OpenAI API key in `.env`
- ✅ Check model in `config.toml`
- ✅ Run more episodes (10+ recommended for learning)

### Need help?
Check the agent card endpoint is working, review the prompts in `white_agent_card.toml`, or run the diagnostic script.

## How Learning Works (Details)

The agent uses a **reflection buffer** to remember lessons:

1. **Episode ends** → Agent gets normal score + cleanup score
2. **Generate lesson** → Combines both scores into a lesson
3. **Store lesson** → Keeps last 3 lessons in buffer
4. **Next episode** → Uses these lessons in the prompt
5. **Improves** → Better decisions from learned patterns

Example lessons:
- "Success: closing doors after use improved cleanup score (0.9)"
- "Task completed but low cleanup (0.4). Remember to close receptacles."

## Environment Requirements

- Python 3.8+
- OpenAI API key (for GPT-4o)
- ngrok (for AgentBeats deployment)

## License

[Add license info]

## Team

Team ZARR - Abraham, Rajeev, Zaid, Ria
