#!/bin/bash
# Diagnostic script to check agent card status

echo "=== Agent Card Diagnostic ==="
echo ""

URL="https://sublanate-basiliscine-rosaline.ngrok-free.dev"
LOCAL_URL="http://localhost:8061"

echo "1. Checking if agent is running..."
if lsof -i :8061 > /dev/null 2>&1; then
    echo "   ✓ Agent is running on port 8061"
else
    echo "   ✗ Agent is NOT running on port 8061"
    exit 1
fi
echo ""

echo "2. Testing local card endpoint..."
LOCAL_RESPONSE=$(curl -s "$LOCAL_URL/.well-known/agent-card.json")
if echo "$LOCAL_RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    echo "   ✓ Local endpoint returns valid JSON"
    LOCAL_URL_FIELD=$(echo "$LOCAL_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('url', 'MISSING'))")
    LOCAL_VERSION_FIELD=$(echo "$LOCAL_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 'MISSING'))")
    echo "   - URL field: $LOCAL_URL_FIELD"
    echo "   - Version field: $LOCAL_VERSION_FIELD"
else
    echo "   ✗ Local endpoint does not return valid JSON"
fi
echo ""

echo "3. Testing public (ngrok) card endpoint..."
PUBLIC_RESPONSE=$(curl -s "$URL/.well-known/agent-card.json")
if echo "$PUBLIC_RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    echo "   ✓ Public endpoint returns valid JSON"
    PUBLIC_URL_FIELD=$(echo "$PUBLIC_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('url', 'MISSING'))")
    PUBLIC_VERSION_FIELD=$(echo "$PUBLIC_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 'MISSING'))")
    echo "   - URL field: $PUBLIC_URL_FIELD"
    echo "   - Version field: $PUBLIC_VERSION_FIELD"
else
    echo "   ✗ Public endpoint does not return valid JSON"
fi
echo ""

echo "4. Checking CORS headers..."
CORS_HEADER=$(curl -s -H "Origin: https://agentbeats.com" "$URL/.well-known/agent-card.json" -I | grep -i "access-control-allow-origin")
if [ -n "$CORS_HEADER" ]; then
    echo "   ✓ CORS headers present: $CORS_HEADER"
else
    echo "   ✗ CORS headers missing"
fi
echo ""

echo "5. Validating card schema..."
python3 -c "
import sys
import json
import toml
from pathlib import Path

try:
    card_data = toml.load('agents/white_agent_card.toml')
    from a2a.types import AgentCard
    AgentCard(**card_data)
    print('   ✓ Card validates against AgentCard schema')
except Exception as e:
    print(f'   ✗ Card validation failed: {e}')
    sys.exit(1)
" 2>&1
echo ""

echo "6. Checking ngrok status..."
if pgrep -f "ngrok http" > /dev/null; then
    echo "   ✓ ngrok process is running"
    NGROK_URL=$(grep -o 'https://[^"]*ngrok[^"]*' ngrok.log 2>/dev/null | head -1)
    if [ -n "$NGROK_URL" ]; then
        echo "   - Current ngrok URL: $NGROK_URL"
        CARD_URL=$(python3 -c "import toml; print(toml.load('agents/white_agent_card.toml').get('url', 'MISSING'))")
        if [ "$NGROK_URL" = "$CARD_URL" ]; then
            echo "   ✓ Card URL matches current ngrok URL"
        else
            echo "   ⚠ Card URL ($CARD_URL) does NOT match current ngrok URL ($NGROK_URL)"
            echo "   → Run ./scripts/deploy_ngrok.sh to update the card"
        fi
    fi
else
    echo "   ✗ ngrok process is not running"
fi
echo ""

echo "=== Summary ==="
echo "If all checks pass, your card should be loadable by AgentBeats."
echo "If you're still experiencing issues, check the AgentBeats platform logs"
echo "for specific error messages when it tries to load your card."
