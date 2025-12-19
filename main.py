"""CLI entry point for ALFWorld White Agent."""

import os
import typer
from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    """Settings loaded from environment variables."""
    role: str = "white"
    host: str = "0.0.0.0"
    agent_port: int = 9002
    agent_url: str = ""

    model_config = {"env_prefix": ""}


app = typer.Typer(help="ALFWorld White Agent - A2A compatible agent for AgentBeats")


@app.command()
def white(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(9002, help="Port to bind to"),
):
    """Start the White Agent server."""
    from white_agent.server import start_white_agent
    start_white_agent(host=host, port=port)


@app.command()
def run():
    """Start the agent based on environment configuration."""
    settings = AgentSettings()
    if settings.role == "white":
        from white_agent.server import start_white_agent
        start_white_agent(host=settings.host, port=settings.agent_port)
    else:
        raise ValueError(f"Unknown role: {settings.role}")


if __name__ == "__main__":
    app()
