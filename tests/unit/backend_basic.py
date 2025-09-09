
"""Basic tests for the Milestone 1 backend scaffold."""

import os
import sys

# Ensure project root is on sys.path so `import backend` works when pytest
# runs from the workspace.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.app import app


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_tools_and_run():
    r = client.get("/tools")
    assert r.status_code == 200
    tools = r.json()
    # echo skill should be present
    names = [t["name"] for t in tools]
    assert "echo" in names

    # Run the echo skill
    r = client.post("/run", json={"name": "echo", "args": {"payload": {"a": 1}}})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["result"]["echo"]["a"] == 1


def test_skill_improvement():
    """Test the skill improvement endpoint."""
    # First, get the current echo skill code
    r = client.get("/skills/echo/code")
    assert r.status_code == 200
    current_code = r.json()["code"]
    
    # Try to improve the skill
    improvement_request = {
        "skill_name": "echo",
        "current_code": current_code,
        "improvement_prompt": "Add input validation to ensure the payload is not None and add a timestamp to the response"
    }
    
    r = client.post("/skills/improve", json=improvement_request)
    assert r.status_code == 200
    body = r.json()
    
    # Check if improvement was successful
    if "OPENAI_API_KEY" in os.environ:
        # If OpenAI API key is available, improvement should succeed
        assert body["success"] is True
        assert "code" in body
        assert body["code"] is not None
        assert "meta" in body
        assert body["meta"]["name"] == "echo"
    else:
        # If no OpenAI API key, it should fail gracefully
        assert body["success"] is False
        assert "error" in body


def test_skill_improvement_nonexistent():
    """Test skill improvement with a non-existent skill."""
    improvement_request = {
        "skill_name": "nonexistent_skill",
        "current_code": "def test(): pass",
        "improvement_prompt": "Make it better"
    }
    
    r = client.post("/skills/improve", json=improvement_request)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is False
    assert "not found" in body["error"].lower()
