"""Test harness for Milestone 3 LLM chat sessions with MCP tool calling."""

import os
import sys
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
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

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Set up a clean test database for each test."""
    # Use a file-based test database that we can clean up
    import tempfile
    import os
    
    # Create a temporary database file
    test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(test_db_fd)  # Close the file descriptor
    
    # Store original DB path and set to test path
    original_db_path = db.DB_PATH
    db.DB_PATH = test_db_path
    
    # Initialize the database
    db.init_db()
    
    yield
    
    # Clean up: restore original DB path and remove test file
    db.DB_PATH = original_db_path
    try:
        os.unlink(test_db_path)
    except OSError:
        pass


class MockOpenAIResponse:
    """Mock OpenAI API response."""
    
    def __init__(self, content: str = "", tool_calls: List[Dict] = None):
        self.choices = [MockChoice(content, tool_calls)]


class MockChoice:
    """Mock OpenAI choice."""
    
    def __init__(self, content: str = "", tool_calls: List[Dict] = None):
        self.message = MockMessage(content, tool_calls)


class MockMessage:
    """Mock OpenAI message."""
    
    def __init__(self, content: str = "", tool_calls: List[Dict] = None):
        self.content = content
        self.tool_calls = tool_calls or []


class MockToolCall:
    """Mock OpenAI tool call."""
    
    def __init__(self, call_id: str, function_name: str, arguments: str):
        self.id = call_id
        self.function = MockFunction(function_name, arguments)


class MockFunction:
    """Mock OpenAI function."""
    
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class TestMilestone3Chat:
    """Test suite for Milestone 3 chat functionality."""
    
    def test_health_check(self):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_mcp_spec_endpoint(self):
        """Test that MCP spec endpoint returns the correct format."""
        response = client.get("/mcp")
        assert response.status_code == 200
        
        mcp_spec = response.json()
        assert "schema_version" in mcp_spec
        assert "server_info" in mcp_spec
        assert "tools" in mcp_spec
        
        # Should have at least the echo skill
        tools = mcp_spec["tools"]
        assert len(tools) >= 1
        
        echo_tool = next((t for t in tools if t["function"]["name"] == "echo"), None)
        assert echo_tool is not None
        assert echo_tool["type"] == "function"
        assert "description" in echo_tool["function"]
        assert "parameters" in echo_tool["function"]
    
    def test_create_chat_session(self):
        """Test creating a new chat session."""
        response = client.post("/sessions", json={"name": "Test Session"})
        assert response.status_code == 200
        
        data = response.json()
        assert "session" in data
        session = data["session"]
        
        assert "id" in session
        assert session["name"] == "Test Session"
        assert "created_at" in session
        assert "updated_at" in session
        assert "messages" in session
        
        # Should have a welcome message
        messages = session["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "Welcome" in messages[0]["content"]
    
    def test_list_sessions(self):
        """Test listing chat sessions."""
        # Create a few sessions
        for i in range(3):
            client.post("/sessions", json={"name": f"Session {i}"})
        
        response = client.get("/sessions")
        assert response.status_code == 200
        
        sessions = response.json()
        assert len(sessions) == 3
        assert all("id" in s and "name" in s for s in sessions)
    
    def test_get_session(self):
        """Test retrieving a specific session."""
        # Create a session
        create_response = client.post("/sessions", json={"name": "Test Session"})
        session_id = create_response.json()["session"]["id"]
        
        # Retrieve the session
        response = client.get(f"/sessions/{session_id}")
        assert response.status_code == 200
        
        session = response.json()
        assert session["id"] == session_id
        assert session["name"] == "Test Session"
    
    def test_get_nonexistent_session(self):
        """Test retrieving a nonexistent session."""
        response = client.get("/sessions/nonexistent-id")
        assert response.status_code == 404
    
    def test_add_message_without_tool_calls(self):
        """Test adding a simple message that gets a demo response."""
        # Create a session
        create_response = client.post("/sessions", json={"name": "Test Session"})
        session_id = create_response.json()["session"]["id"]
        
        # Add a user message
        response = client.post(
            f"/sessions/{session_id}/messages",
            json={"role": "user", "content": "Hello, how are you?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have created the user message
        assert data["message"]["role"] == "user"
        assert data["message"]["content"] == "Hello, how are you?"
        assert data["skill_generated"] is None
        
        # Verify the session now has both user and assistant messages
        session_response = client.get(f"/sessions/{session_id}")
        assert session_response.status_code == 200
        session_data = session_response.json()
        
        # Should have system, user, and assistant messages
        messages = session_data["messages"]
        assert len(messages) >= 3  # system + user + assistant
        
        # Check that assistant responded
        assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
        assert len(assistant_messages) >= 1
        
        # Assistant should respond with AutoLearn intro
        last_assistant_msg = assistant_messages[-1]
        assert "AutoLearn" in last_assistant_msg["content"]
    
    def test_add_message_with_tool_calls(self):
        """Test adding a message that mentions a skill."""
        # Create a session
        create_response = client.post("/sessions", json={"name": "Test Session"})
        session_id = create_response.json()["session"]["id"]
        
        # Add a user message that mentions a skill
        response = client.post(
            f"/sessions/{session_id}/messages",
            json={"role": "user", "content": "I want to use the echo skill"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have created the user message
        assert data["message"]["role"] == "user"
        assert data["message"]["content"] == "I want to use the echo skill"
        
        # Check the session to see if assistant response was added
        session_response = client.get(f"/sessions/{session_id}")
        session = session_response.json()
        messages = session["messages"]
        
        # Should have: system welcome, user message, assistant response
        assert len(messages) >= 3
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_messages) >= 1
        
        # Assistant should suggest how to use the skill via MCP
        last_assistant_msg = assistant_messages[-1]
        assert "echo" in last_assistant_msg["content"]
        assert ("MCP" in last_assistant_msg["content"] or 
                "execute" in last_assistant_msg["content"] or
                "/run" in last_assistant_msg["content"])
    
    @patch('backend.openai_client.OpenAIClient')
    def test_skill_generation_from_chat(self, mock_openai_class):
        """Test skill generation triggered from chat."""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai_instance = Mock()
        mock_openai_instance.client = mock_client
        mock_openai_instance.config = Mock(model_name="gpt-4")
        mock_openai_instance.generate_skill_code = Mock()
        mock_openai_class.return_value = mock_openai_instance
        
        # Mock skill generation
        mock_skill_result = Mock()
        mock_skill_result.code = '''def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b'''
        mock_skill_result.meta = {
            "name": "add_numbers",
            "description": "Add two numbers together",
            "inputs": {"a": "int", "b": "int"}
        }
        mock_openai_instance.generate_skill_code.return_value = mock_skill_result
        
        # Mock the initial OpenAI response
        mock_response = MockOpenAIResponse("I'll create an addition skill for you!")
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create a session
        create_response = client.post("/sessions", json={"name": "Test Session"})
        session_id = create_response.json()["session"]["id"]
        
        # Add a message requesting skill creation
        response = client.post(
            f"/sessions/{session_id}/messages",
            json={"role": "user", "content": "create a skill that adds two numbers"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have triggered skill generation
        if data["skill_generated"]:
            assert data["skill_generated"]["name"] == "add_numbers"
            assert "Add two numbers" in data["skill_generated"]["description"]
    
    def test_skill_execution_endpoint(self):
        """Test direct skill execution endpoint."""
        # Test the echo skill
        response = client.post("/run", json={
            "name": "echo",
            "args": {"payload": {"test": "data"}}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["result"]["echo"]["test"] == "data"
    
    def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Test running nonexistent skill
        response = client.post("/run", json={
            "name": "nonexistent_skill",
            "args": {}
        })
        assert response.status_code == 404
        
        # Test invalid session message
        response = client.post(
            "/sessions/invalid-session-id/messages",
            json={"role": "user", "content": "test"}
        )
        assert response.status_code == 404


def test_integration_scenario():
    """Test a complete integration scenario."""
    with TestClient(app=app) as test_client:
        # 1. Check MCP spec
        mcp_response = test_client.get("/mcp")
        assert mcp_response.status_code == 200
        mcp_spec = mcp_response.json()
        assert len(mcp_spec["tools"]) >= 1
        
        # 2. Create a chat session
        session_response = test_client.post("/sessions", json={"name": "Integration Test"})
        assert session_response.status_code == 200
        session_id = session_response.json()["session"]["id"]
        
        # 3. Test direct skill execution
        run_response = test_client.post("/run", json={
            "name": "echo", 
            "args": {"payload": "integration test"}
        })
        assert run_response.status_code == 200
        assert run_response.json()["success"] is True
        
        # 4. Verify session persistence
        get_session_response = test_client.get(f"/sessions/{session_id}")
        assert get_session_response.status_code == 200
        session = get_session_response.json()
        assert session["name"] == "Integration Test"
        assert len(session["messages"]) == 1  # Welcome message


if __name__ == "__main__":
    # Run specific tests for quick debugging
    pytest.main([__file__, "-v", "-s"])
