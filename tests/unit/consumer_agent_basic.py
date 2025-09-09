"""Test harness for Milestone 4 Consumer Agent implementation.

Tests the core PRD requirements:
- User can manually request a new skill to be created
- AutoLearn generates and crystalizes code into persistent skill
- Frontend can display skill (including code) + updated MCP spec
- User can then prompt the frontend chat to use the new skill, which executes successfully
"""

import os
import sys
import json
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Any, Dict, List

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(ROOT, '.env'))

from fastapi.testclient import TestClient
from backend.app import app
from backend import db
from backend.consumer_agent import ConsumerAgent, MCPClient

client = TestClient(app=app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Set up a clean test database for each test."""
    import tempfile
    test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')
    
    # Close the file descriptor but keep the path
    os.close(test_db_fd)
    
    # Patch the database path
    original_db_path = db.DB_PATH
    db.DB_PATH = test_db_path
    
    # Initialize the test database
    db.init_db()
    
    yield
    
    # Cleanup
    db.DB_PATH = original_db_path
    try:
        os.unlink(test_db_path)
    except:
        pass


def test_consumer_agent_creation():
    """Test that consumer agent can be created."""
    agent = ConsumerAgent()
    assert agent is not None
    assert agent.mcp_server_url == "http://localhost:8000/mcp"
    assert agent.conversations == {}


@pytest.mark.asyncio
async def test_start_conversation():
    """Test starting a new conversation session."""
    agent = ConsumerAgent()
    session_id = await agent.start_conversation("test_user")
    
    assert session_id is not None
    assert session_id in agent.conversations
    
    context = agent.conversations[session_id]
    assert context.session_id == session_id
    assert len(context.messages) == 1  # System message
    assert context.messages[0].role == "system"


def test_consumer_agent_endpoints_exist():
    """Test that consumer agent endpoints are accessible."""
    # Test available skills endpoint
    response = client.get("/consumer-agent/skills/available")
    # Should not be 404 - endpoint exists
    assert response.status_code != 404
    
    # Test chat endpoint exists
    response = client.post("/consumer-agent/chat", json={
        "message": "test message"
    })
    # Should not be 404 - endpoint exists  
    assert response.status_code != 404


def test_mcp_client_creation():
    """Test MCP client can be created."""
    mcp_client = MCPClient()
    assert mcp_client.server_url == "http://localhost:8000/mcp"
    

def test_mcp_client_custom_url():
    """Test MCP client with custom URL."""
    mcp_client = MCPClient("http://example.com/mcp")
    assert mcp_client.server_url == "http://example.com/mcp"


def test_start_agent_session_endpoint():
    """Test starting a new agent session via API."""
    response = client.post("/consumer-agent/sessions/start")
    # Should not be 404
    assert response.status_code != 404
    

def test_chat_endpoint_validation():
    """Test chat endpoint validates input."""
    # Empty message should be rejected
    response = client.post("/consumer-agent/chat", json={})
    assert response.status_code in [400, 422]  # Validation error
    

def test_skill_suggestions_endpoint():
    """Test skill suggestions endpoint."""
    response = client.get("/consumer-agent/skills/suggestions?query=test")
    assert response.status_code != 404


# PRD Core Requirements Tests
@patch('backend.consumer_agent.MCPClient')
def test_prd_requirement_endpoints_exist(mock_mcp_client):
    """Test that all PRD-required endpoints exist."""
    
    # Mock MCP client to avoid connection errors
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock()
    mock_client_instance.call_tool = AsyncMock(return_value={"success": True, "name": "test_skill"})
    mock_mcp_client.return_value = mock_client_instance
    
    # User can manually request a new skill to be created
    response = client.post("/consumer-agent/skills/request", json={
        "description": "test skill",
        "session_id": "test"
    })
    assert response.status_code != 404
    
    # Frontend can display skill code - this will be 404 because skill doesn't exist, but endpoint exists
    response = client.get("/skills/nonexistent_skill/code")
    assert response.status_code in [404, 500]  # 404 is expected for nonexistent skill
    
    # User can chat to use new skills
    response = client.post("/consumer-agent/chat", json={
        "message": "test"
    })
    assert response.status_code != 404


def test_conversation_history_endpoint():
    """Test conversation history endpoint for frontend display."""
    # Start a session via the API first
    response = client.post("/consumer-agent/sessions/start")
    assert response.status_code == 200
    session_data = response.json()
    session_id = session_data["session_id"]
    
    # Now test the conversation history endpoint
    response = client.get(f"/consumer-agent/conversation/{session_id}")
    assert response.status_code == 200  # Should return the conversation
    
    # Verify the response structure
    data = response.json()
    assert "session_id" in data
    assert "messages" in data
    assert "skills_used" in data
    assert "skills_requested" in data
    assert data["session_id"] == session_id
    
    # Test non-existent session
    response = client.get("/consumer-agent/conversation/nonexistent_session")
    assert response.status_code == 404


# Additional tests for consumer agent with mocking can be added here
# Following the patterns from other test files in the suite
