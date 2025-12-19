# ALFWorld White Agent

A reflection-augmented GPT-4o agent for ALFWorld household tasks, compatible with [AgentBeats](https://agentbeats.ai) via the A2A protocol.

## Features

- **Structured Workflow**: Understand → Explore → Interact → Manipulate → Complete
- **Multi-Objective Behavior**: Task completion + cleanup awareness (close containers after use)
- **Cross-Episode Reflection**: Learns from past episodes with behavior-focused lessons
- **Repetition & Cycle Detection**: Avoids getting stuck in loops
- **A2A Protocol Compatible**: Works with AgentBeats evaluation framework

## Prerequisites

- Python 3.10+
- OpenAI API key
- [ngrok](https://ngrok.com/) account (for public URL)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/alfworld-whiteagent.git
cd alfworld-whiteagent

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```bash
# Required: Your OpenAI API key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Required for AgentBeats: Your ngrok public URL (set after starting ngrok)
AGENT_URL=https://your-subdomain.ngrok-free.dev
```

## Quick Start

### 1. Start ngrok (in Terminal 1)

```bash
ngrok http 9002
```

Copy the forwarding URL (e.g., `https://abc123.ngrok-free.dev`)

### 2. Update `.env` with ngrok URL

```bash
echo "AGENT_URL=https://abc123.ngrok-free.dev" >> .env
```

### 3. Start the Agent Server (in Terminal 2)

```bash
python main.py white --port 9002
```

You should see:
```
Starting ALFWorld White Agent on 0.0.0.0:9002...
Agent URL: https://abc123.ngrok-free.dev
Agent card will be available at: https://abc123.ngrok-free.dev/.well-known/agent.json
Status endpoint: https://abc123.ngrok-free.dev/status
```

### 4. Verify the Agent is Running

```bash
# Check status endpoint
curl https://your-subdomain.ngrok-free.dev/status
# Expected: {"status":"ok","agent":"ALFWorld White Agent","version":"1.1.0","ready":true}

# Check agent card
curl https://your-subdomain.ngrok-free.dev/.well-known/agent.json
```

### 5. Register in AgentBeats

1. Go to [AgentBeats](https://agentbeats.ai)
2. Add a new agent
3. Enter your ngrok URL: `https://your-subdomain.ngrok-free.dev`
4. AgentBeats will automatically fetch the agent card from `/.well-known/agent.json`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Health check, returns `{"status": "ok", ...}` |
| `/health` | GET | Simple health check |
| `/.well-known/agent.json` | GET | A2A Agent Card |
| `/` | POST | JSON-RPC endpoint for task execution |

## Project Structure

```
alfworld-whiteagent/
├── main.py                  # CLI entry point
├── white_agent/
│   ├── agent.py             # Core agent logic (reflection, actions)
│   └── server.py            # A2A server (exposes agent card, handles requests)
├── agents/
│   └── white_agent_card.toml  # (legacy reference, not used by server)
├── requirements.txt
├── .env                     # Your config (not committed)
├── .env.example             # Template for .env
└── run.sh                   # Alternative start script
```

## How It Works

1. **Agent Card Serving**: The server programmatically creates an `AgentCard` using the A2A SDK and serves it at `/.well-known/agent.json`

2. **Task Execution**: When AgentBeats sends a task:
   - The `ALFWorldAgentExecutor` receives the request
   - It creates/retrieves a `WhiteAgent` instance for the context
   - The agent processes the observation and returns an action
   - The action is sent back via the A2A protocol

3. **Reflection Learning**: After each episode:
   - The agent summarizes what worked/failed
   - Lessons (e.g., "close containers after use") are stored
   - Next episode's prompt includes the last 3 lessons

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |
| `AGENT_URL` | Yes | Your public ngrok URL |
| `MODEL` | No | LLM model to use (default: `gpt-4o`) |

## Troubleshooting

### Agent card not loading in AgentBeats
- Ensure `AGENT_URL` in `.env` matches your ngrok URL exactly
- Restart the server after changing `.env`
- Verify with `curl https://your-url/.well-known/agent.json`

### 404 on /status
- Make sure you're running the latest code
- Restart the server: `python main.py white --port 9002`

### ngrok URL changed
- Free ngrok URLs change on restart
- Update `AGENT_URL` in `.env` and restart the server

## License

MIT
