import pytest
from white_agent.agent import WhiteAgent


def test_full_episode_mock(monkeypatch):
    # Mock environment loop
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = WhiteAgent()
    obs = agent.reset("You see a table.")

    done = False
    max_steps = 5
    step = 0

    while not done and step < max_steps:
        action = agent.act(obs)
        # Mock environment response
        next_obs = f"You {action}."
        reward = 0.1
        done = step == max_steps - 1

        agent.observe(action, reward, done, {})
        obs = next_obs
        step += 1

    assert agent.state["done"] is True
    assert agent.state["step"] == max_steps
