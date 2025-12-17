# ALFWorld White Agent

This repository contains the implementation of the White Agent for ALFWorld, designed to act as an ASSESSSEE evaluated by the Green Agent.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configuration:
   Adjust `white_agent/config.toml` for policy settings and hyperparameters.

## Usage

### Running Locally
You can run the agent evaluation script:
```bash
python scripts/evaluate_white_agent.py
```

The agent keeps a tiny reflection buffer of recent lessons (success/fail cues and any evaluator feedback). Each new episode prepends those lessons to the prompt to encourage quick adaptation to the assessor’s scoring.

### AgentBeats Deployment

**Option 1: Direct Agent Deployment (current)**
To deploy with AgentBeats and ngrok:
```bash
./scripts/deploy_ngrok.sh
```

**Option 2: Controller Pattern (recommended for AgentBeats platform)**
To use the controller pattern for better AgentBeats integration:
```bash
# The controller will manage the agent lifecycle
agentbeats run agents/white_agent_card.toml \
    --agent_host 0.0.0.0 \
    --agent_port 8061 \
    --model_type openai \
    --model_name gpt-4o
```

Note: The controller pattern provides better integration with the AgentBeats platform, including agent lifecycle management and proper agent card loading.

## Testing
Run unit and integration tests:
```bash
pytest tests/
```
