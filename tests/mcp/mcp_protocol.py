"""
Unit tests for MCP Protocol implementation.

Tests that the MCP protocol handler correctly implements the MCP specification.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock

from backend.mcp_protocol import (
    MCPProtocolHandler, MCPRequest, MCPResponse, MCPNotification,
    MCPServerInfo, MCPServerCapabilities, MCPTool, MCPContent,
    MCPErrorCode
)
from backend.skill_engine import SkillEngine, SkillMeta


class TestMCPProtocolHandler:
    """Test the core MCP protocol handler."""
    
    @pytest.fixture
    def mock_skill_engine(self):
        """Create a mock skill engine with test skills."""
        engine = Mock(spec=SkillEngine)
        
        # Mock skills
        echo_skill = SkillMeta(
            name="echo",
            description="Return the input payload",
            inputs={"payload": "any"}
        )
        
        multiply_skill = SkillMeta(
            name="multiply_numbers", 
            description="Multiplies two numbers together",
            inputs={"a": "float", "b": "float"}
        )
        
        engine.list_skills.return_value = [echo_skill, multiply_skill]
        engine.run.return_value = "mocked result"
        
        return engine
    
    @pytest.fixture
    def handler(self, mock_skill_engine):
        """Create MCP protocol handler with mock skill engine."""
        return MCPProtocolHandler(mock_skill_engine)
    
    def test_initialization(self, handler):
        """Test that handler initializes correctly."""
        assert handler.protocol_version == "2025-06-18"
        assert handler.server_info.name == "AutoLearn"
        assert handler.server_info.version == "0.1.0"
        assert handler.capabilities.tools == {"listChanged": True}
        assert not handler.initialized
    
    @pytest.mark.asyncio
    async def test_initialize_request(self, handler):
        """Test MCP initialization handshake."""
        # Valid initialization request
        message = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        response = await handler.handle_message(json.dumps(message))
        response_data = json.loads(response)
        
        # Verify response structure
        assert response_data["jsonrpc"] == "2.0"
        assert response_data["id"] == "test-1"
        assert "result" in response_data
        
        result = response_data["result"]
        assert result["protocolVersion"] == "2025-06-18"
        assert result["serverInfo"]["name"] == "AutoLearn"
        assert result["serverInfo"]["version"] == "0.1.0"
        assert result["capabilities"]["tools"]["listChanged"] is True
        
        # Handler should now be initialized
        assert handler.initialized
    
    @pytest.mark.asyncio
    async def test_tools_list_request(self, handler, mock_skill_engine):
        """Test tools/list request returns proper MCP tools format."""
        # Initialize first
        handler.initialized = True
        
        message = {
            "jsonrpc": "2.0",
            "id": "test-2",
            "method": "tools/list"
        }
        
        response = await handler.handle_message(json.dumps(message))
        response_data = json.loads(response)
        
        # Verify response structure
        assert response_data["jsonrpc"] == "2.0"
        assert response_data["id"] == "test-2"
        assert "result" in response_data
        
        result = response_data["result"]
        assert "tools" in result
        tools = result["tools"]
        
        # Should have 2 tools from mock
        assert len(tools) == 2
        
        # Verify echo tool format
        echo_tool = next(t for t in tools if t["name"] == "echo")
        assert echo_tool["description"] == "Return the input payload"
        assert echo_tool["inputSchema"]["type"] == "object"
        assert "payload" in echo_tool["inputSchema"]["properties"]
        assert echo_tool["inputSchema"]["required"] == ["payload"]
        
        # Verify multiply tool format  
        multiply_tool = next(t for t in tools if t["name"] == "multiply_numbers")
        assert multiply_tool["description"] == "Multiplies two numbers together"
        assert "a" in multiply_tool["inputSchema"]["properties"]
        assert "b" in multiply_tool["inputSchema"]["properties"]
        assert set(multiply_tool["inputSchema"]["required"]) == {"a", "b"}
    
    @pytest.mark.asyncio
    async def test_tools_call_request(self, handler, mock_skill_engine):
        """Test tools/call request executes skill correctly."""
        # Initialize first
        handler.initialized = True
        
        message = {
            "jsonrpc": "2.0",
            "id": "test-3", 
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"payload": "Hello MCP!"}
            }
        }
        
        response = await handler.handle_message(json.dumps(message))
        response_data = json.loads(response)
        
        # Verify response structure
        assert response_data["jsonrpc"] == "2.0"
        assert response_data["id"] == "test-3" 
        assert "result" in response_data
        
        result = response_data["result"]
        assert "content" in result
        assert "isError" in result
        assert result["isError"] is False
        
        # Verify content format
        content = result["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "mocked result"
        
        # Verify skill engine was called correctly
        mock_skill_engine.run.assert_called_once_with("echo", {"payload": "Hello MCP!"})
    
    @pytest.mark.asyncio
    async def test_tools_call_error_handling(self, handler, mock_skill_engine):
        """Test tools/call error handling."""
        # Initialize first
        handler.initialized = True
        
        # Make skill engine raise an error
        mock_skill_engine.run.side_effect = Exception("Skill execution failed")
        
        message = {
            "jsonrpc": "2.0",
            "id": "test-4",
            "method": "tools/call", 
            "params": {
                "name": "echo",
                "arguments": {"payload": "test"}
            }
        }
        
        response = await handler.handle_message(json.dumps(message))
        response_data = json.loads(response)
        
        # Should return error in content, not JSON-RPC error
        assert response_data["jsonrpc"] == "2.0"
        assert response_data["id"] == "test-4"
        assert "result" in response_data
        
        result = response_data["result"]
        assert result["isError"] is True
        assert "content" in result
        
        content = result["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert "Error: Skill execution failed" in content[0]["text"]
    
    @pytest.mark.asyncio
    async def test_method_not_found(self, handler):
        """Test handling of unknown methods."""
        message = {
            "jsonrpc": "2.0",
            "id": "test-5",
            "method": "unknown/method"
        }
        
        response = await handler.handle_message(json.dumps(message))
        response_data = json.loads(response)
        
        # Should return JSON-RPC error
        assert response_data["jsonrpc"] == "2.0"
        assert response_data["id"] == "test-5"
        assert "error" in response_data
        
        error = response_data["error"]
        assert error["code"] == MCPErrorCode.METHOD_NOT_FOUND.value
        assert "Method not found" in error["message"]
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, handler):
        """Test handling of invalid JSON."""
        invalid_json = "{invalid json"
        
        response = await handler.handle_message(invalid_json)
        response_data = json.loads(response)
        
        # Should return parse error
        assert response_data["jsonrpc"] == "2.0"
        assert response_data["id"] is None
        assert "error" in response_data
        
        error = response_data["error"]
        assert error["code"] == MCPErrorCode.PARSE_ERROR.value
        assert "Invalid JSON" in error["message"]
    
    @pytest.mark.asyncio
    async def test_notification_no_response(self, handler):
        """Test that notifications don't return responses."""
        # Notification has no id field
        message = {
            "jsonrpc": "2.0", 
            "method": "notifications/initialized"
        }
        
        response = await handler.handle_message(json.dumps(message))
        
        # Should return None for notifications
        assert response is None
    
    @pytest.mark.asyncio
    async def test_tools_changed_notification(self, handler):
        """Test tools changed notification generation."""
        notification_json = await handler.send_tools_changed_notification()
        notification_data = json.loads(notification_json)
        
        assert notification_data["jsonrpc"] == "2.0"
        assert notification_data["method"] == "notifications/tools/list_changed"
        assert "id" not in notification_data  # Notifications have no id
    
    @pytest.mark.asyncio
    async def test_not_initialized_error(self, handler):
        """Test that requests fail when not initialized."""
        # Don't initialize handler
        assert not handler.initialized
        
        message = {
            "jsonrpc": "2.0",
            "id": "test-6",
            "method": "tools/list"
        }
        
        response = await handler.handle_message(json.dumps(message))
        response_data = json.loads(response)
        
        # Should return internal error
        assert "error" in response_data
        assert response_data["error"]["code"] == MCPErrorCode.INTERNAL_ERROR.value
        assert "Not initialized" in response_data["error"]["message"]


class TestMCPDataStructures:
    """Test MCP data structure classes."""
    
    def test_mcp_request_from_dict(self):
        """Test MCPRequest creation from dict."""
        data = {
            "jsonrpc": "2.0",
            "method": "test/method",
            "id": "test-1",
            "params": {"key": "value"}
        }
        
        request = MCPRequest.from_dict(data)
        assert request.jsonrpc == "2.0"
        assert request.method == "test/method"
        assert request.id == "test-1"
        assert request.params == {"key": "value"}
    
    def test_mcp_response_to_dict(self):
        """Test MCPResponse serialization."""
        response = MCPResponse(
            jsonrpc="2.0",
            id="test-1",
            result={"key": "value"}
        )
        
        data = response.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-1"
        assert data["result"] == {"key": "value"}
        assert "error" not in data
    
    def test_mcp_response_error_to_dict(self):
        """Test MCPResponse error serialization."""
        response = MCPResponse(
            jsonrpc="2.0",
            id="test-1",
            error={"code": -32601, "message": "Method not found"}
        )
        
        data = response.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-1"
        assert data["error"]["code"] == -32601
        assert "result" not in data
    
    def test_mcp_notification_to_dict(self):
        """Test MCPNotification serialization."""
        notification = MCPNotification(
            jsonrpc="2.0",
            method="notifications/test",
            params={"key": "value"}
        )
        
        data = notification.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "notifications/test"
        assert data["params"] == {"key": "value"}
        assert "id" not in data
    
    def test_mcp_content_to_dict(self):
        """Test MCPContent serialization."""
        content = MCPContent(type="text", text="Hello World")
        
        data = content.to_dict()
        assert data["type"] == "text"
        assert data["text"] == "Hello World"
