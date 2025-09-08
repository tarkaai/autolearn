"""WebSocket implementation for AutoLearn."""

import logging
import socketio
from fastapi import FastAPI

logger = logging.getLogger("autolearn.websocket")

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Create an ASGI app from the Socket.IO server
socket_app = socketio.ASGIApp(sio)

# Events to emit
SKILL_ADDED = "skill_added"
SKILL_EXECUTED = "skill_executed"
MCP_UPDATED = "mcp_updated"


async def setup_socketio(app: FastAPI) -> None:
    """Set up Socket.IO with the FastAPI app.
    
    Args:
        app: The FastAPI application
    """
    # Mount the Socket.IO app at /ws
    app.mount('/ws', socket_app)
    logger.info("WebSocket server mounted at /ws")
    
    # Set up event handlers
    @sio.event
    async def connect(sid, environ):
        """Handle client connection."""
        logger.info(f"Client connected: {sid}")
        # Send welcome message
        await sio.emit('welcome', {'message': 'Welcome to AutoLearn WebSocket!'}, room=sid)
    
    @sio.event
    async def disconnect(sid):
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {sid}")


async def emit_skill_added(skill_meta):
    """Emit event when a skill is added.
    
    Args:
        skill_meta: The metadata of the added skill
    """
    logger.info(f"Emitting skill_added event for {skill_meta.get('name', 'unknown')}")
    await sio.emit(SKILL_ADDED, skill_meta)


async def emit_skill_executed(execution_result):
    """Emit event when a skill is executed.
    
    Args:
        execution_result: The result of the skill execution
    """
    logger.info(f"Emitting skill_executed event")
    await sio.emit(SKILL_EXECUTED, execution_result)


async def emit_mcp_updated(mcp_spec):
    """Emit event when the MCP spec is updated.
    
    Args:
        mcp_spec: The updated MCP spec
    """
    logger.info(f"Emitting mcp_updated event")
    await sio.emit(MCP_UPDATED, mcp_spec)
