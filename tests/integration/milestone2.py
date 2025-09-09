"""Tests for Milestone 2 OpenAI integration and dynamic skill generation."""

import os
import sys
from typing import Any, Dict
from unittest.mock import MagicMock

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.schemas import SkillMeta
from backend.openai_client import CodeGenerationResult
from backend.skill_engine import create_default_engine


# Sample generated code for a simple calculator skill
SAMPLE_CODE = '''
def calculator(operation: str, a: float, b: float) -> dict:
    """A simple calculator function.

    Args:
        operation: Operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number

    Returns:
        Dictionary with the result
    """
    result = None
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")
    
    return {"result": result}
'''

SAMPLE_META = {
    "name": "calculator",
    "description": "A simple calculator that can add, subtract, multiply, and divide",
    "version": "0.1.0",
    "inputs": {
        "operation": "string",
        "a": "number",
        "b": "number"
    }
}


@pytest.fixture
def client():
    """Create a test client with mocked OpenAI client."""
    # Initialize app state with engine and OpenAI client
    app.state.engine = create_default_engine()
    
    # Create mock OpenAI client
    mock_client = MagicMock()
    mock_client.generate_skill_code.return_value = CodeGenerationResult(
        code=SAMPLE_CODE,
        meta=SAMPLE_META
    )
    app.state.openai_client = mock_client
    
    # Create test client
    test_client = TestClient(app=app)
    
    yield test_client


def test_generate_skill(client):
    """Test generating a skill from natural language."""
    response = client.post(
        "/skills/generate",
        json={
            "description": "Create a calculator that can add, subtract, multiply, and divide",
            "name": "calculator"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "code" in data
    assert "meta" in data
    assert data["meta"]["name"] == "calculator"


def test_register_skill(client):
    """Test registering a generated skill."""
    # First generate the skill
    gen_response = client.post(
        "/skills/generate",
        json={
            "description": "Create a calculator that can add, subtract, multiply, and divide",
            "name": "calculator"
        }
    )
    assert gen_response.status_code == 200
    gen_data = gen_response.json()
    
    # Now register it
    reg_response = client.post(
        "/skills/register",
        json={
            "code": gen_data["code"],
            "meta": gen_data["meta"]
        }
    )
    
    assert reg_response.status_code == 200
    reg_data = reg_response.json()
    assert reg_data["success"] is True
    assert reg_data["name"] == "calculator"
    
    # Verify the skill appears in the tools list
    tools_response = client.get("/tools")
    assert tools_response.status_code == 200
    tools = tools_response.json()
    assert any(tool["name"] == "calculator" for tool in tools)
    
    # Verify the skill appears in the MCP spec
    mcp_response = client.get("/mcp")
    assert mcp_response.status_code == 200
    mcp = mcp_response.json()
    assert any(tool["function"]["name"] == "calculator" for tool in mcp["tools"])


def test_run_registered_skill(client):
    """Test running a registered skill."""
    # First register the skill
    meta = SkillMeta(**SAMPLE_META)
    reg_response = client.post(
        "/skills/register",
        json={
            "code": SAMPLE_CODE,
            "meta": meta.dict()
        }
    )
    assert reg_response.status_code == 200
    
    # Now run it
    run_response = client.post(
        "/run",
        json={
            "name": "calculator",
            "args": {
                "operation": "add",
                "a": 5,
                "b": 3
            }
        }
    )
    
    assert run_response.status_code == 200
    run_data = run_response.json()
    assert run_data["success"] is True
    assert run_data["result"]["result"] == 8  # 5 + 3 = 8
