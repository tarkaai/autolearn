"""
Model Context Protocol (MCP) implementation for AutoLearn server.

This module implements the MCP specification for exposing AutoLearn skills
as MCP tools to connecting clients like Claude Desktop.

MCP Specification: https://modelcontextprotocol.io/specification/2025-06-18/
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class MCPErrorCode(Enum):
    """Standard JSON-RPC 2.0 error codes used by MCP."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class MCPRequest:
    """MCP JSON-RPC request message."""
    jsonrpc: str
    method: str
    id: Optional[Union[str, int]] = None
    params: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPRequest':
        return cls(
            jsonrpc=data.get('jsonrpc', '2.0'),
            method=data['method'],
            id=data.get('id'),
            params=data.get('params')
        )


@dataclass
class MCPResponse:
    """MCP JSON-RPC response message."""
    jsonrpc: str
    id: Union[str, int]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'jsonrpc': self.jsonrpc, 'id': self.id}
        if self.result is not None:
            result['result'] = self.result
        if self.error is not None:
            result['error'] = self.error
        return result


@dataclass
class MCPNotification:
    """MCP JSON-RPC notification message (no response expected)."""
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'jsonrpc': self.jsonrpc, 'method': self.method}
        if self.params is not None:
            result['params'] = self.params
        return result


@dataclass
class MCPServerInfo:
    """MCP server information."""
    name: str
    version: str


@dataclass
class MCPServerCapabilities:
    """MCP server capabilities."""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class MCPContent:
    """MCP content object for responses."""
    type: str
    text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'type': self.type}
        if self.text is not None:
            result['text'] = self.text
        return result


class MCPProtocolHandler:
    """
    Core MCP protocol handler implementing JSON-RPC 2.0 over various transports.
    
    This class handles the MCP protocol lifecycle, message routing, and
    core primitives like tools, resources, and prompts.
    """
    
    def __init__(self, skill_engine=None):
        self.skill_engine = skill_engine
        self.initialized = False
        self.protocol_version = "2025-06-18"
        
        # Server info
        self.server_info = MCPServerInfo(
            name="AutoLearn",
            version="0.1.0"
        )
        
        # Server capabilities
        self.capabilities = MCPServerCapabilities(
            tools={"listChanged": True}  # We support tool change notifications
        )
        
        # Method handlers
        self.handlers: Dict[str, Callable] = {
            'initialize': self._handle_initialize,
            'tools/list': self._handle_tools_list,
            'tools/call': self._handle_tools_call,
        }
        
        logger.info(f"MCP Protocol Handler initialized - {self.server_info.name} v{self.server_info.version}")
    
    async def handle_message(self, message: str) -> Optional[str]:
        """
        Handle incoming MCP message and return response (if not a notification).
        
        Args:
            message: JSON-RPC message string
            
        Returns:
            JSON response string, or None for notifications
        """
        try:
            data = json.loads(message)
            logger.debug(f"Received MCP message: {data.get('method', 'unknown')}")
            
            # Parse request
            if 'method' not in data:
                return self._error_response(None, MCPErrorCode.INVALID_REQUEST, "Missing method")
            
            request = MCPRequest.from_dict(data)
            
            # Handle the request
            if request.method in self.handlers:
                try:
                    result = await self.handlers[request.method](request)
                    
                    # If no ID, this is a notification - no response
                    if request.id is None:
                        return None
                    
                    # Return successful response
                    response = MCPResponse(
                        jsonrpc="2.0",
                        id=request.id,
                        result=result
                    )
                    return json.dumps(response.to_dict())
                    
                except Exception as e:
                    logger.error(f"Error handling {request.method}: {str(e)}")
                    if request.id is not None:
                        return self._error_response(
                            request.id, 
                            MCPErrorCode.INTERNAL_ERROR, 
                            str(e)
                        )
            else:
                if request.id is not None:
                    return self._error_response(
                        request.id,
                        MCPErrorCode.METHOD_NOT_FOUND,
                        f"Method not found: {request.method}"
                    )
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            return self._error_response(None, MCPErrorCode.PARSE_ERROR, "Invalid JSON")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return self._error_response(None, MCPErrorCode.INTERNAL_ERROR, str(e))
        
        return None
    
    def _error_response(self, request_id: Optional[Union[str, int]], 
                       error_code: MCPErrorCode, message: str) -> str:
        """Generate JSON-RPC error response."""
        response = MCPResponse(
            jsonrpc="2.0",
            id=request_id,
            error={
                "code": error_code.value,
                "message": message
            }
        )
        return json.dumps(response.to_dict())
    
    async def _handle_initialize(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle MCP initialization handshake."""
        params = request.params or {}
        
        # Validate protocol version  
        client_version = params.get('protocolVersion')
        if client_version != self.protocol_version:
            logger.warning(f"Protocol version mismatch: client={client_version}, server={self.protocol_version}")
        
        # Log client info
        client_info = params.get('clientInfo', {})
        logger.info(f"MCP client connected: {client_info.get('name', 'unknown')} v{client_info.get('version', 'unknown')}")
        
        # Mark as initialized
        self.initialized = True
        
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": asdict(self.capabilities),
            "serverInfo": asdict(self.server_info)
        }
    
    async def _handle_tools_list(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/list request - return available skills as MCP tools."""
        if not self.initialized:
            raise Exception("Not initialized")
        
        if not self.skill_engine:
            return {"tools": []}
        
        # Convert skills to MCP tools format
        tools = []
        for skill_meta in self.skill_engine.list_skills():
            # Generate JSON Schema for inputs
            input_schema = {
                "type": "object",
                "properties": {
                    name: {"type": type_name} 
                    for name, type_name in skill_meta.inputs.items()
                },
                "required": list(skill_meta.inputs.keys())
            }
            
            mcp_tool = MCPTool(
                name=skill_meta.name,
                description=skill_meta.description,
                inputSchema=input_schema
            )
            tools.append(asdict(mcp_tool))
        
        logger.info(f"Returning {len(tools)} MCP tools")
        return {"tools": tools}
    
    async def _handle_tools_call(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/call request - execute a skill."""
        if not self.initialized:
            raise Exception("Not initialized")
        
        if not self.skill_engine:
            raise Exception("No skill engine available")
        
        params = request.params or {}
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if not tool_name:
            raise Exception("Missing tool name")
        
        logger.info(f"Executing MCP tool: {tool_name} with args: {arguments}")
        
        try:
            # Execute the skill
            result = self.skill_engine.run(tool_name, arguments)
            
            # Format response as MCP content
            content = [MCPContent(type="text", text=str(result)).to_dict()]
            
            return {
                "content": content,
                "isError": False
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            # Return error as content
            content = [MCPContent(type="text", text=f"Error: {str(e)}").to_dict()]
            return {
                "content": content,
                "isError": True
            }
    
    async def send_tools_changed_notification(self) -> str:
        """Send notification that available tools have changed."""
        notification = MCPNotification(
            jsonrpc="2.0",
            method="notifications/tools/list_changed"
        )
        return json.dumps(notification.to_dict())
