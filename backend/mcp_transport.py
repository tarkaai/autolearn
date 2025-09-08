"""
MCP Transport layer implementation for AutoLearn.

Supports stdio and HTTP transports as defined in the MCP specification.
"""

import asyncio
import sys
import json
import logging
from typing import Optional, Callable, Any
from abc import ABC, abstractmethod

from .mcp_protocol import MCPProtocolHandler

logger = logging.getLogger(__name__)


class MCPTransport(ABC):
    """Abstract base class for MCP transport implementations."""
    
    def __init__(self, protocol_handler: MCPProtocolHandler):
        self.protocol_handler = protocol_handler
        self.running = False
    
    @abstractmethod
    async def start(self):
        """Start the transport layer."""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the transport layer."""
        pass


class MCPStdioTransport(MCPTransport):
    """
    MCP stdio transport implementation.
    
    This transport communicates over stdin/stdout using JSON-RPC messages,
    one message per line. This is the primary transport for desktop MCP clients
    like Claude Desktop.
    """
    
    def __init__(self, protocol_handler: MCPProtocolHandler):
        super().__init__(protocol_handler)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
    
    async def start(self):
        """Start stdio transport - read from stdin, write to stdout."""
        logger.info("Starting MCP stdio transport")
        self.running = True
        
        try:
            # Set up stdin/stdout streams
            self.reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(self.reader)
            
            # Connect to stdin
            loop = asyncio.get_event_loop()
            transport, _ = await loop.connect_read_pipe(
                lambda: protocol, sys.stdin
            )
            
            # Set up stdout writer
            stdout_transport, stdout_protocol = await loop.connect_write_pipe(
                asyncio.StreamReaderProtocol, sys.stdout
            )
            self.writer = asyncio.StreamWriter(stdout_transport, stdout_protocol, self.reader, loop)
            
            # Send server ready message
            logger.info("MCP stdio transport ready - waiting for client connection")
            
            # Message processing loop
            await self._message_loop()
            
        except Exception as e:
            logger.error(f"MCP stdio transport error: {str(e)}")
            raise
        finally:
            self.running = False
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
    
    async def stop(self):
        """Stop stdio transport."""
        logger.info("Stopping MCP stdio transport")
        self.running = False
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
    
    async def _message_loop(self):
        """Main message processing loop."""
        while self.running and self.reader:
            try:
                # Read line from stdin
                line = await self.reader.readline()
                if not line:  # EOF
                    logger.info("MCP client disconnected (EOF)")
                    break
                
                message = line.decode('utf-8').strip()
                if not message:
                    continue
                
                logger.debug(f"Received: {message}")
                
                # Handle the message
                response = await self.protocol_handler.handle_message(message)
                
                # Send response if there is one (not for notifications)
                if response and self.writer:
                    logger.debug(f"Sending: {response}")
                    self.writer.write((response + '\n').encode('utf-8'))
                    await self.writer.drain()
                    
            except asyncio.CancelledError:
                logger.info("MCP transport cancelled")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {str(e)}")
                # Continue processing other messages
                continue
        
        logger.info("MCP message loop ended")
    
    async def send_notification(self, notification: str):
        """Send a notification message to the client."""
        if self.writer and self.running:
            logger.debug(f"Sending notification: {notification}")
            self.writer.write((notification + '\n').encode('utf-8'))
            await self.writer.drain()


class MCPHTTPTransport(MCPTransport):
    """
    MCP HTTP transport implementation (future).
    
    This transport would use HTTP POST for requests and optionally
    Server-Sent Events for notifications.
    """
    
    def __init__(self, protocol_handler: MCPProtocolHandler, host: str = "localhost", port: int = 8001):
        super().__init__(protocol_handler)
        self.host = host
        self.port = port
        self.app = None
    
    async def start(self):
        """Start HTTP transport (not implemented yet)."""
        logger.warning("MCP HTTP transport not yet implemented")
        raise NotImplementedError("HTTP transport coming soon")
    
    async def stop(self):
        """Stop HTTP transport."""
        pass


class MCPServer:
    """
    Main MCP Server that coordinates protocol handling and transport.
    
    This is the main entry point for running an AutoLearn MCP server.
    """
    
    def __init__(self, skill_engine=None, transport_type: str = "stdio"):
        self.skill_engine = skill_engine
        self.transport_type = transport_type
        
        # Create protocol handler
        self.protocol_handler = MCPProtocolHandler(skill_engine)
        
        # Create transport
        if transport_type == "stdio":
            self.transport = MCPStdioTransport(self.protocol_handler)
        elif transport_type == "http":
            self.transport = MCPHTTPTransport(self.protocol_handler)
        else:
            raise ValueError(f"Unknown transport type: {transport_type}")
        
        logger.info(f"MCP Server created with {transport_type} transport")
    
    async def run(self):
        """Run the MCP server."""
        logger.info("Starting AutoLearn MCP Server")
        logger.info(f"Protocol version: {self.protocol_handler.protocol_version}")
        logger.info(f"Server capabilities: {self.protocol_handler.capabilities}")
        
        try:
            await self.transport.start()
        except KeyboardInterrupt:
            logger.info("MCP Server shutdown requested")
        except Exception as e:
            logger.error(f"MCP Server error: {str(e)}")
            raise
        finally:
            await self.transport.stop()
            logger.info("AutoLearn MCP Server stopped")
    
    async def notify_tools_changed(self):
        """Notify connected clients that available tools have changed."""
        if hasattr(self.transport, 'send_notification'):
            notification = await self.protocol_handler.send_tools_changed_notification()
            await self.transport.send_notification(notification)
