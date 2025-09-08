"""Session management for AutoLearn chat."""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from . import db
from .schemas import ChatSession, ChatMessage, AddMessageRequest, CreateSessionRequest

logger = logging.getLogger("autolearn.sessions")

def create_session(request: CreateSessionRequest) -> ChatSession:
    """Create a new chat session.
    
    Args:
        request: Session creation request
        
    Returns:
        The created session
    """
    session_id = str(uuid.uuid4())
    now = datetime.now()
    
    session = ChatSession(
        id=session_id,
        name=request.name,
        created_at=now,
        updated_at=now,
        messages=[]
    )
    
    # Add a welcome message
    welcome_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="system",
        content="Welcome to AutoLearn! How can I help you today?",
        timestamp=now
    )
    
    # Store in database
    session.messages = [welcome_msg]
    db.create_session(session)
    
    logger.info(f"Created new session: {session_id} ({request.name})")
    return session


def get_session(session_id: str) -> Optional[ChatSession]:
    """Get a chat session by ID.
    
    Args:
        session_id: ID of the session to retrieve
        
    Returns:
        The session if found, None otherwise
    """
    return db.get_session(session_id)


def list_sessions() -> List[ChatSession]:
    """List all chat sessions.
    
    Returns:
        List of all sessions
    """
    return db.list_sessions()


def add_message(session_id: str, request: AddMessageRequest) -> Optional[ChatMessage]:
    """Add a message to a chat session.
    
    Args:
        session_id: ID of the session to add the message to
        request: Message to add
        
    Returns:
        The created message if successful, None if session not found
    """
    # Check if session exists
    session = get_session(session_id)
    if not session:
        return None
    
    # Create message
    message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=request.role,
        content=request.content,
        timestamp=datetime.now()
    )
    
    # Add to database
    db.add_message(message)
    
    logger.info(f"Added message to session {session_id}: {message.role}")
    return message
