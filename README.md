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
To deploy with AgentBeats and ngrok:
```bash
./scripts/deploy_ngrok.sh
```

## Testing
Run unit and integration tests:
```bash
pytest tests/
```
