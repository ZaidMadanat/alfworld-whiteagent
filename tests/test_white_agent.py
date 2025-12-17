import pytest
from white_agent.agent import WhiteAgent
import toml

def test_initialization():
    agent = WhiteAgent()
    assert agent.policy_type in ["rule_based", "random", "neural"]
    assert agent.state == {}

def test_reset():
    agent = WhiteAgent()
    initial_obs = "You are in a room."
    obs = agent.reset(initial_obs)
    assert obs == initial_obs
    assert agent.state["step"] == 0
    assert "history" in agent.state
    assert len(agent.state["history"]) == 1

def test_act():
    agent = WhiteAgent()
    agent.reset("start")
    action = agent.act("observation")
    assert isinstance(action, str)
    assert len(action) > 0
    assert "ACT: " in agent.state["history"][-1]

def test_observe():
    agent = WhiteAgent()
    agent.reset("start")
    agent.observe("look", 0.0, False, {})
    assert agent.state["step"] == 1
    assert agent.state["last_reward"] == 0.0
    assert agent.state["done"] is False
