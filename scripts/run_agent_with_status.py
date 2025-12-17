#!/usr/bin/env python
import argparse
import importlib.util
import pathlib
import sys

from agentbeats.agent_executor import BeatsAgent
from agentbeats import get_registered_tools
from starlette.responses import JSONResponse
from starlette.routing import Route


def _import_tool_file(path: str):
    """Import a Python file so any @agentbeats.tool decorators register."""
    file_path = pathlib.Path(path).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # Prevent garbage collection
    spec.loader.exec_module(module)


class StatusBeatsAgent(BeatsAgent):
    """BeatsAgent with a lightweight /status endpoint for health checks."""

    def _make_app(self):
        super()._make_app()

        @self.app.route("/status")
        async def _status(_request):
            return JSONResponse({"status": "ok"})

        def _card_payload():
            """Return agent card with both camelCase and snake_case for compatibility."""
            payload = dict(self.agent_card_json)
            # Add snake_case mirrors expected by some consumers
            if "defaultInputModes" in payload and "default_input_modes" not in payload:
                payload["default_input_modes"] = payload["defaultInputModes"]
            if "defaultOutputModes" in payload and "default_output_modes" not in payload:
                payload["default_output_modes"] = payload["defaultOutputModes"]
            if "preferredTransport" in payload and "preferred_transport" not in payload:
                payload["preferred_transport"] = payload["preferredTransport"]
            if "protocolVersion" in payload and "protocol_version" not in payload:
                payload["protocol_version"] = payload["protocolVersion"]
            if "supportsAuthenticatedExtendedCard" in payload and "supports_authenticated_extended_card" not in payload:
                payload["supports_authenticated_extended_card"] = payload["supportsAuthenticatedExtendedCard"]
            return payload

        def _card_endpoint(_request):
            return JSONResponse(_card_payload())

        # Add extra aliases for card endpoints to satisfy different consumers.
        card_paths = [
            "/agent-card.json",
            "/agent-card",
            "/agent.json",
            "/.well-known/agent-card.json",
            "/.well-known/agent.json",
        ]
        for path in card_paths:
            self.app.routes.insert(0, Route(path, _card_endpoint, methods=["GET", "HEAD"]))


def main():
    parser = argparse.ArgumentParser(
        description="Run AgentBeats agent with /status endpoint"
    )
    parser.add_argument("card", help="path/to/agent_card.toml")
    parser.add_argument("--agent_host", default="0.0.0.0")
    parser.add_argument("--agent_port", type=int, default=8061)
    parser.add_argument("--model_type", default="openai")
    parser.add_argument("--model_name", default="gpt-4o")
    parser.add_argument(
        "--tool", action="append", default=[], help="Python file(s) exporting @agentbeats.tool functions"
    )
    parser.add_argument(
        "--mcp", action="append", default=[], help="MCP SSE server URL(s)"
    )

    args = parser.parse_args()

    # Load any tool files so decorators can register
    for tool_file in args.tool:
        _import_tool_file(tool_file)

    agent = StatusBeatsAgent(
        name="white-agent",
        agent_host=args.agent_host,
        agent_port=args.agent_port,
        model_type=args.model_type,
        model_name=args.model_name,
    )

    for func in get_registered_tools():
        agent.register_tool(func)

    agent.load_agent_card(args.card)

    for url in args.mcp:
        if url:
            agent.add_mcp_server(url)

    agent.run()


if __name__ == "__main__":
    main()
