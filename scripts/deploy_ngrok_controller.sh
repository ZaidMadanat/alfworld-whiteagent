#!/bin/bash
# scripts/deploy_ngrok_controller.sh
# Deploy with AgentBeats controller pattern

# Ensure ngrok and agentbeats are installed
if ! command -v ngrok &> /dev/null; then
    echo "ngrok could not be found. Please install it first."
    exit 1
fi

CONTROLLER_PORT=8080
AGENT_PORT=8061

# Cleanup previous instances
pkill -f "ngrok http $CONTROLLER_PORT"
pkill -f "agentbeats run"

echo "Starting ngrok on controller port $CONTROLLER_PORT..."
ngrok http $CONTROLLER_PORT --log=stdout > ngrok.log &
NGROK_PID=$!

echo "Waiting for ngrok to initialize..."
sleep 5

# Extract public URL
PUBLIC_URL=$(grep -o 'https://[^"]*ngrok[^"]*' ngrok.log | head -1)

if [ -z "$PUBLIC_URL" ]; then
    # Fallback to catching any https url that looks like a tunnel if the above fails
    PUBLIC_URL=$(grep -o 'https://[^"]*\.trycloudflare\.com' ngrok.log | head -1)
fi

if [ -z "$PUBLIC_URL" ]; then
    echo "Failed to get ngrok URL. Check ngrok.log"
    kill $NGROK_PID
    exit 1
fi

echo "Ngrok URL: $PUBLIC_URL"

# Update card with new URL (controller URL)
perl -pi -e "s|url\s*=\s*\".*\"|url = \"$PUBLIC_URL\"|g" agents/white_agent_card.toml

echo "Updated agents/white_agent_card.toml with controller URL."

# Start the agent with controller
echo "Starting AgentBeats controller on port $CONTROLLER_PORT (agent on $AGENT_PORT)..."
source .venv/bin/activate
agentbeats run agents/white_agent_card.toml \
    --agent_host 0.0.0.0 \
    --agent_port $AGENT_PORT \
    --launcher_port $CONTROLLER_PORT \
    --model_type openai \
    --model_name gpt-4o &
AGENT_PID=$!

echo ""
echo "Controller deployed at: $PUBLIC_URL"
echo "Controller port: $CONTROLLER_PORT"
echo "Agent port: $AGENT_PORT (internal)"
echo ""
echo "Use the controller URL ($PUBLIC_URL) in AgentBeats platform."
echo "Ready for evaluation. Press Ctrl+C to stop."

wait

