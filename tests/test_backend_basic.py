
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
