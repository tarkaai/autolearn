"""
Integration tests for MCP Server FastAPI implementation.

Tests that the MCP server correctly integrates with FastAPI and 
provides proper MCP protocol over HTTP transport.
"""

import pytest
import json
import asyncio
from httpx import AsyncClient

from backend.app import app
from backend.mcp_protocol import MCPProtocolHandler
from backend.skill_engine import get_engine


class TestMCPFastAPIIntegration:
    """Test MCP server integration with FastAPI."""
    
    @pytest.fixture(autouse=True)
    def setup_app_state(self):
        """Initialize app state for testing."""
        # Initialize the skill engine and MCP handler
        engine = get_engine() 
        app.state.mcp_handler = MCPProtocolHandler(engine)
        yield
        # Cleanup if needed
    
    @pytest.mark.asyncio
    async def test_mcp_endpoint_exists(self):
        """Test that /mcp endpoint exists and accepts POST requests."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test with valid MCP initialization
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
            
            response = await client.post("/mcp", json=message)
            assert response.status_code == 200
            
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "test-1"
            assert "result" in data
    
    @pytest.mark.asyncio
    async def test_mcp_initialization_flow(self):
        """Test complete MCP initialization flow."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Initialize
            init_message = {
                "jsonrpc": "2.0", 
                "id": "init-1",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "integration-test", "version": "1.0.0"}
                }
            }
            
            response = await client.post("/mcp", json=init_message)
            assert response.status_code == 200
            
            data = response.json()
            result = data["result"]
            
            # Verify server info
            assert result["serverInfo"]["name"] == "AutoLearn"
            assert result["serverInfo"]["version"] == "0.1.0"
            assert result["protocolVersion"] == "2025-06-18"
            
            # Verify capabilities
            assert result["capabilities"]["tools"]["listChanged"] is True
    
    @pytest.mark.asyncio
    async def test_mcp_tools_discovery(self):
        """Test MCP tools discovery after initialization."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": "init-1", 
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
            await client.post("/mcp", json=init_message)
            
            # List tools
            tools_message = {
                "jsonrpc": "2.0",
                "id": "tools-1",
                "method": "tools/list"
            }
            
            response = await client.post("/mcp", json=tools_message)
            assert response.status_code == 200
            
            data = response.json()
            result = data["result"]
            tools = result["tools"]
            
            # Should have at least echo and multiply_numbers tools
            tool_names = {tool["name"] for tool in tools}
            assert "echo" in tool_names
            assert "multiply_numbers" in tool_names
            
            # Verify tool schema format
            echo_tool = next(t for t in tools if t["name"] == "echo")
            assert "description" in echo_tool
            assert "inputSchema" in echo_tool
            assert echo_tool["inputSchema"]["type"] == "object" 
            assert "properties" in echo_tool["inputSchema"]
            assert "required" in echo_tool["inputSchema"]
    
    @pytest.mark.asyncio 
    async def test_mcp_tool_execution_format(self):
        """Test MCP tool execution returns proper format (even if sandbox fails)."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": "init-1",
                "method": "initialize", 
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
            await client.post("/mcp", json=init_message)
            
            # Call tool
            call_message = {
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "echo",
                    "arguments": {"payload": "test message"}
                }
            }
            
            response = await client.post("/mcp", json=call_message)
            assert response.status_code == 200
            
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "call-1"
            assert "result" in data
            
            result = data["result"]
            # Verify MCP tool response format
            assert "content" in result
            assert "isError" in result
            assert isinstance(result["content"], list)
            
            # Content should have proper structure
            if result["content"]:
                content = result["content"][0]
                assert "type" in content
                assert content["type"] == "text"
                assert "text" in content
    
    @pytest.mark.asyncio
    async def test_mcp_error_handling(self):
        """Test MCP error handling for various scenarios."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test invalid JSON-RPC (missing method)
            invalid_message = {
                "jsonrpc": "2.0",
                "id": "invalid-1"
                # Missing method field
            }
            
            response = await client.post("/mcp", json=invalid_message)
            assert response.status_code == 200  # MCP errors are 200 with error in body
            
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -32600  # Invalid Request
    
    @pytest.mark.asyncio
    async def test_mcp_unknown_method(self):
        """Test handling of unknown MCP methods."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            unknown_message = {
                "jsonrpc": "2.0", 
                "id": "unknown-1",
                "method": "unknown/method"
            }
            
            response = await client.post("/mcp", json=unknown_message)
            assert response.status_code == 200
            
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -32601  # Method not found
            assert "Method not found" in data["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_mcp_notification_no_response(self):
        """Test that MCP notifications return 204 No Content."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Send notification (no id field)
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            response = await client.post("/mcp", json=notification)
            assert response.status_code == 204  # No Content for notifications
    
    @pytest.mark.asyncio
    async def test_mcp_specification_compliance(self):
        """Test that MCP implementation complies with specification requirements."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test full MCP flow according to specification
            
            # 1. Initialize
            init_response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "spec-init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "spec-test", "version": "1.0.0"}
                }
            })
            
            init_data = init_response.json()
            
            # Verify initialization response structure
            assert "result" in init_data
            init_result = init_data["result"]
            
            # Required fields per MCP spec
            assert "protocolVersion" in init_result
            assert "serverInfo" in init_result
            assert "capabilities" in init_result
            
            server_info = init_result["serverInfo"]
            assert "name" in server_info
            assert "version" in server_info 
            
            capabilities = init_result["capabilities"]
            assert "tools" in capabilities
            
            # 2. Send initialized notification
            await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            })
            
            # 3. Discover tools
            tools_response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "spec-tools",
                "method": "tools/list"
            })
            
            tools_data = tools_response.json()
            assert "result" in tools_data
            assert "tools" in tools_data["result"]
            
            # Verify tool format per MCP spec
            tools = tools_data["result"]["tools"]
            if tools:  # If we have tools
                tool = tools[0]
                # Required fields per MCP spec
                assert "name" in tool
                assert "description" in tool  
                assert "inputSchema" in tool
                
                schema = tool["inputSchema"]
                assert "type" in schema
                assert schema["type"] == "object"
                assert "properties" in schema


class TestMCPServerCapabilities:
    """Test MCP server capabilities and compliance."""
    
    @pytest.fixture(autouse=True) 
    def setup_app_state(self):
        """Initialize app state for testing."""
        engine = get_engine()
        app.state.mcp_handler = MCPProtocolHandler(engine)
        yield
    
    @pytest.mark.asyncio
    async def test_server_declares_correct_capabilities(self):
        """Test that server declares correct capabilities during initialization."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "cap-test",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18", 
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "cap-test", "version": "1.0.0"}
                }
            })
            
            data = response.json()
            capabilities = data["result"]["capabilities"]
            
            # AutoLearn should support tools with change notifications
            assert "tools" in capabilities
            assert capabilities["tools"]["listChanged"] is True
            
            # Currently we don't support resources or prompts
            assert capabilities.get("resources") is None
            assert capabilities.get("prompts") is None
    
    @pytest.mark.asyncio
    async def test_protocol_version_support(self):
        """Test protocol version handling."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test with correct protocol version
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "version-test",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            data = response.json()
            assert "result" in data
            assert data["result"]["protocolVersion"] == "2025-06-18"
    
    @pytest.mark.asyncio
    async def test_json_rpc_compliance(self):
        """Test JSON-RPC 2.0 compliance."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # All responses should have jsonrpc: "2.0"
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "rpc-test",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "rpc-test"
            
            # Either result or error, but not both
            assert ("result" in data) != ("error" in data)
