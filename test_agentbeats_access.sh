#!/bin/bash
# Test script to check what AgentBeats sees

URL="https://sublanate-basiliscine-rosaline.ngrok-free.dev"

echo "Testing agent card access for AgentBeats..."
echo "=========================================="
echo ""

echo "1. Testing base URL:"
curl -s "$URL" | head -5
echo ""
echo "---"

echo "2. Testing agent card endpoint:"
curl -s "$URL/.well-known/agent-card.json" | python -m json.tool 2>&1 | head -10
echo ""
echo "---"

echo "3. Testing with User-Agent header (simulating AgentBeats):"
curl -A "AgentBeats/1.0" -s "$URL/.well-known/agent-card.json" | python -m json.tool 2>&1 | head -10
echo ""
echo "---"

echo "4. Checking response headers:"
curl -I -s "$URL/.well-known/agent-card.json" | head -10

