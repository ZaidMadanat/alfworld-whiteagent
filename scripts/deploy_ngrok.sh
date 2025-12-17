#!/bin/bash
# scripts/deploy_ngrok.sh

# Ensure ngrok and agentbeats are installed
if ! command -v ngrok &> /dev/null; then
    echo "ngrok could not be found. Please install it first."
    exit 1
fi

PORT=8061

# Cleanup previous instances
pkill -f "ngrok http $PORT"
pkill -f "agentbeats run agents/white_agent_card.toml"

echo "Starting ngrok on port $PORT..."
ngrok http $PORT --log=stdout > ngrok.log &
NGROK_PID=$!

echo "Waiting for ngrok to initialize..."
sleep 5

# Extract public URL
# Pattern matches standard ngrok domains (ngrok-free.app, ngrok-free.dev, ngrok.io, etc.)
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

# Update card with new URL
# Use perl to handle the replacement with flexible whitespace before '='
perl -pi -e "s|url\s*=\s*\".*\"|url = \"$PUBLIC_URL\"|g" agents/white_agent_card.toml

echo "Updated agents/white_agent_card.toml with public URL."

# Start the agent using agentbeats standard runner
# We configure it to use OpenAI GPT-4o as tested
echo "Starting White Agent on port $PORT..."
agentbeats run agents/white_agent_card.toml \
    --agent_host 0.0.0.0 \
    --agent_port $PORT \
    --model_type openai \
    --model_name gpt-4o \
    --launcher_host 127.0.0.1 \
    --launcher_port 9000 &
AGENT_PID=$!

echo "Agent deployed at: $PUBLIC_URL"
echo "Ready for evaluation. Press Ctrl+C to stop."

wait
