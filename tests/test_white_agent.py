import pytest

from white_agent.agent import WhiteAgent


def test_initialization(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = WhiteAgent()

    assert agent.policy_type in ["rule_based", "random", "neural"]
    assert agent.model
    assert agent.state == {}


def test_reset(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = WhiteAgent()
    initial_obs = "You are in a room."

    obs = agent.reset(initial_obs)

    assert obs == initial_obs
    assert agent.state["step"] == 0
    assert len(agent.state["history"]) == 2
    assert agent.state["history"][0]["role"] == "system"
    assert "Observation: You are in a room." in agent.state["history"][1]["content"]


def test_act_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = WhiteAgent()
    agent.reset("start")

    action = agent.act("lamp is off")

    assert isinstance(action, str)
    assert len(action) > 0
    assert agent.state["history"][-1]["role"] == "assistant"


def test_observe(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = WhiteAgent()
    agent.reset("start")

    agent.observe("look", 0.0, False, {})

    assert agent.state["step"] == 1
    assert agent.state["last_reward"] == 0.0
    assert agent.state["done"] is False

    agent.observe("look", 1.0, True, {})
    assert agent.state["done"] is True
    # Last entries include end-of-episode message and lesson
    assert any("Episode finished." in msg["content"] for msg in agent.state["history"] if msg["role"] == "user")
    assert any("Lesson learned" in msg["content"] for msg in agent.state["history"] if msg["role"] == "system")
