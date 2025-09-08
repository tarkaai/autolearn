"""
MCP Specification compliance tests.

These tests verify that AutoLearn implements the MCP specification correctly
according to the official documentation at https://modelcontextprotocol.io/
"""

import pytest
import json
import asyncio
from httpx import AsyncClient

from backend.app import app


class TestMCPSpecificationCompliance:
    """Test compliance with MCP specification requirements."""
    
    @pytest.mark.asyncio
    async def test_mcp_lifecycle_management(self):
        """
        Test MCP lifecycle management as per specification.
        
        From MCP spec: "MCP is a stateful protocol that requires lifecycle management.
        The purpose of lifecycle management is to negotiate the capabilities that 
        both client and server support."
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Client sends initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": "lifecycle-1",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {
                        "elicitation": {}  # Client capability from spec example
                    },
                    "clientInfo": {
                        "name": "autolearn-compliance-test",
                        "version": "1.0.0"
                    }
                }
            }
            
            response = await client.post("/mcp", json=init_request)
            assert response.status_code == 200
            
            data = response.json()
            
            # Verify response structure per spec
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "lifecycle-1"
            assert "result" in data
            
            result = data["result"]
            
            # Required fields per MCP specification
            assert "protocolVersion" in result
            assert "capabilities" in result
            assert "serverInfo" in result
            
            # Protocol version negotiation
            assert result["protocolVersion"] == "2025-06-18"
            
            # Server info structure
            server_info = result["serverInfo"]
            assert "name" in server_info
            assert "version" in server_info
            assert server_info["name"] == "AutoLearn"
            assert server_info["version"] == "0.1.0"
            
            # Capabilities structure
            capabilities = result["capabilities"]
            assert "tools" in capabilities
            assert capabilities["tools"]["listChanged"] is True
            
            # Step 2: Client sends initialized notification
            initialized_notification = {
                "jsonrpc": "2.0", 
                "method": "notifications/initialized"
            }
            
            notify_response = await client.post("/mcp", json=initialized_notification)
            assert notify_response.status_code == 204  # No content for notifications
    
    @pytest.mark.asyncio
    async def test_mcp_tools_primitive(self):
        """
        Test MCP tools primitive as per specification.
        
        From MCP spec: "Tools: Executable functions that AI applications can invoke 
        to perform actions (e.g., file operations, API calls, database queries)"
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Initialize first
            await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "tools-test", "version": "1.0.0"}
                }
            })
            
            # Test tools/list method
            tools_request = {
                "jsonrpc": "2.0",
                "id": "tools-list-1",
                "method": "tools/list"
            }
            
            response = await client.post("/mcp", json=tools_request)
            assert response.status_code == 200
            
            data = response.json()
            assert "result" in data
            assert "tools" in data["result"]
            
            tools = data["result"]["tools"]
            
            # Verify tool structure per MCP spec
            for tool in tools:
                # Required fields per specification
                assert "name" in tool
                assert "description" in tool
                assert "inputSchema" in tool
                
                # Name should be unique identifier
                assert isinstance(tool["name"], str)
                assert len(tool["name"]) > 0
                
                # Description should be human-readable
                assert isinstance(tool["description"], str)
                assert len(tool["description"]) > 0
                
                # inputSchema should be JSON Schema
                schema = tool["inputSchema"]
                assert "type" in schema
                assert schema["type"] == "object"
                
                if "properties" in schema:
                    assert isinstance(schema["properties"], dict)
                
                if "required" in schema:
                    assert isinstance(schema["required"], list)
    
    @pytest.mark.asyncio
    async def test_mcp_tools_execution(self):
        """
        Test MCP tools execution as per specification.
        
        From MCP spec: "The client can now execute a tool using the tools/call method."
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Initialize
            await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "exec-test", "version": "1.0.0"}
                }
            })
            
            # Execute tool
            call_request = {
                "jsonrpc": "2.0",
                "id": "tool-call-1",
                "method": "tools/call",
                "params": {
                    "name": "echo",
                    "arguments": {
                        "payload": "MCP specification test"
                    }
                }
            }
            
            response = await client.post("/mcp", json=call_request)
            assert response.status_code == 200
            
            data = response.json()
            assert "result" in data
            
            result = data["result"]
            
            # Verify response structure per MCP spec
            assert "content" in result
            assert isinstance(result["content"], list)
            
            # Content should be array of content objects
            content = result["content"]
            if content:  # If there's content
                content_item = content[0]
                assert "type" in content_item
                
                # Per spec, text content should have type and text fields
                if content_item["type"] == "text":
                    assert "text" in content_item
    
    @pytest.mark.asyncio  
    async def test_mcp_json_rpc_compliance(self):
        """
        Test JSON-RPC 2.0 compliance as required by MCP.
        
        From MCP spec: "MCP uses JSON-RPC 2.0 as its underlying RPC protocol.
        Client and servers send requests to each other and respond accordingly."
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test request-response correlation
            request_id = "json-rpc-test-123"
            
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize", 
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "rpc-test", "version": "1.0.0"}
                }
            })
            
            data = response.json()
            
            # JSON-RPC 2.0 requirements
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == request_id  # Response ID must match request ID
            
            # Must have either result or error, but not both
            has_result = "result" in data
            has_error = "error" in data
            assert has_result != has_error  # XOR - exactly one should be true
    
    @pytest.mark.asyncio
    async def test_mcp_error_codes(self):
        """
        Test MCP error handling with proper JSON-RPC error codes.
        
        From JSON-RPC 2.0 spec (used by MCP):
        -32700: Parse error
        -32600: Invalid Request  
        -32601: Method not found
        -32602: Invalid params
        -32603: Internal error
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test method not found
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "error-test-1",
                "method": "nonexistent/method"
            })
            
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -32601  # Method not found
            assert "Method not found" in data["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_mcp_notifications(self):
        """
        Test MCP notifications as per specification.
        
        From MCP spec: "Notifications can be used when no response is required."
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Notifications have no id field
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
                # No id field for notifications
            }
            
            response = await client.post("/mcp", json=notification)
            
            # Notifications should return 204 No Content
            assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_mcp_capability_negotiation(self):
        """
        Test MCP capability negotiation as per specification.
        
        From MCP spec: "The capabilities object allows each party to declare what 
        features they support, including which primitives they can handle (tools, 
        resources, prompts) and whether they support features like notifications."
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Client declares its capabilities
            client_capabilities = {
                "tools": {},
                "elicitation": {}  # Client can handle user interaction requests
            }
            
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "capability-test",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": client_capabilities,
                    "clientInfo": {"name": "capability-test", "version": "1.0.0"}
                }
            })
            
            data = response.json()
            server_capabilities = data["result"]["capabilities"]
            
            # Verify server declares its capabilities correctly
            
            # AutoLearn supports tools with change notifications
            assert "tools" in server_capabilities
            assert server_capabilities["tools"]["listChanged"] is True
            
            # AutoLearn doesn't currently support resources or prompts
            # (These should be None or missing, not empty objects)
            assert server_capabilities.get("resources") is None
            assert server_capabilities.get("prompts") is None


class TestAutoLearnMCPSpecificFeatures:
    """Test AutoLearn-specific MCP features."""
    
    @pytest.mark.asyncio
    async def test_dynamic_skill_registration_as_tools(self):
        """
        Test that AutoLearn skills appear as MCP tools.
        
        This is the core value proposition of AutoLearn - dynamic skill creation
        that immediately becomes available as MCP tools.
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Initialize MCP connection
            await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}}, 
                    "clientInfo": {"name": "skill-test", "version": "1.0.0"}
                }
            })
            
            # Get initial tools list
            initial_response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "tools-1",
                "method": "tools/list"
            })
            
            initial_tools = initial_response.json()["result"]["tools"]
            initial_tool_names = {tool["name"] for tool in initial_tools}
            
            # Should have default skills (echo, multiply_numbers)
            assert "echo" in initial_tool_names
            assert "multiply_numbers" in initial_tool_names
            
            # Verify skills are properly formatted as MCP tools
            echo_tool = next(t for t in initial_tools if t["name"] == "echo")
            
            # Should have all required MCP tool fields
            assert "name" in echo_tool
            assert "description" in echo_tool
            assert "inputSchema" in echo_tool
            
            # Schema should be valid JSON Schema
            schema = echo_tool["inputSchema"]
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "payload" in schema["properties"]
            assert "required" in schema
            assert "payload" in schema["required"]
    
    @pytest.mark.asyncio
    async def test_autolearn_server_identification(self):
        """Test that AutoLearn properly identifies itself in MCP handshake."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "identity-test",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            data = response.json()
            server_info = data["result"]["serverInfo"]
            
            # AutoLearn should identify itself correctly
            assert server_info["name"] == "AutoLearn"
            assert server_info["version"] == "0.1.0"
    
    @pytest.mark.asyncio
    async def test_autolearn_tool_change_notifications_capability(self):
        """
        Test that AutoLearn declares support for tool change notifications.
        
        This is important because AutoLearn dynamically creates new skills,
        so clients need to know when the tool list changes.
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": "notification-capability-test",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            data = response.json()
            capabilities = data["result"]["capabilities"]
            
            # AutoLearn MUST support tool change notifications
            # because skills can be dynamically created
            assert "tools" in capabilities
            assert capabilities["tools"]["listChanged"] is True
