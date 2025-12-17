#!/bin/bash
# Script for AgentBeats controller to launch the agent
# The controller will set HOST and AGENT_PORT environment variables

python scripts/run_agent_with_status.py agents/white_agent_card.toml \
    --agent_host ${HOST:-0.0.0.0} \
    --agent_port ${AGENT_PORT:-8061} \
    --model_type openai \
    --model_name gpt-4o

