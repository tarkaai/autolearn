"""Database module for AutoLearn."""

import os
import json
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from datetime import datetime

from .schemas import SkillMeta, ChatSession, ChatMessage

logger = logging.getLogger("autolearn.db")

# Get the database file path
DB_PATH = os.environ.get("AUTOLEARN_DB_PATH", "skills.db")

# SQL statements for skills table
CREATE_SKILLS_TABLE = """
CREATE TABLE IF NOT EXISTS skills (
    name TEXT PRIMARY KEY,
    description TEXT,
    version TEXT NOT NULL,
    inputs TEXT NOT NULL,
    code TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

# SQL statements for sessions table
CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

# SQL statements for messages table
CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    skill_generated TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
)
"""

@contextmanager
def get_db_connection():
    """Get a database connection with auto-close."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize the database with required tables."""
    try:
        with get_db_connection() as conn:
            conn.execute(CREATE_SKILLS_TABLE)
            conn.execute(CREATE_SESSIONS_TABLE)
            conn.execute(CREATE_MESSAGES_TABLE)
            conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")
        return True
    except Exception as e:
        logger.exception(f"Error initializing database: {e}")
        return False

# Skill operations
def save_skill(skill: SkillMeta, code: str) -> bool:
    """Save a skill to the database.
    
    Args:
        skill: Skill metadata
        code: Skill code
        
    Returns:
        True if successful, False otherwise
    """
    now = datetime.now().isoformat()
    try:
        with get_db_connection() as conn:
            # Check if skill exists
            cursor = conn.execute("SELECT name FROM skills WHERE name = ?", (skill.name,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update existing skill
                conn.execute(
                    """UPDATE skills SET 
                    description = ?, 
                    version = ?, 
                    inputs = ?, 
                    code = ?, 
                    updated_at = ? 
                    WHERE name = ?""",
                    (
                        skill.description,
                        skill.version,
                        json.dumps(skill.inputs),
                        code,
                        now,
                        skill.name,
                    ),
                )
            else:
                # Insert new skill
                conn.execute(
                    """INSERT INTO skills 
                    (name, description, version, inputs, code, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        skill.name,
                        skill.description,
                        skill.version,
                        json.dumps(skill.inputs),
                        code,
                        now,
                        now,
                    ),
                )
            conn.commit()
        logger.info(f"Skill saved: {skill.name}")
        return True
    except Exception as e:
        logger.exception(f"Error saving skill {skill.name}: {e}")
        return False

def get_skill(name: str) -> tuple[Optional[SkillMeta], Optional[str]]:
    """Get a skill from the database.
    
    Args:
        name: Skill name
        
    Returns:
        Tuple of (SkillMeta, code) if found, (None, None) otherwise
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT name, description, version, inputs, code FROM skills WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            
            if not row:
                return None, None
                
            # Create SkillMeta object
            meta = SkillMeta(
                name=row["name"],
                description=row["description"],
                version=row["version"],
                inputs=json.loads(row["inputs"]),
            )
            
            return meta, row["code"]
    except Exception as e:
        logger.exception(f"Error getting skill {name}: {e}")
        return None, None

def delete_skill(name: str) -> bool:
    """Delete a skill from the database.
    
    Args:
        name: Skill name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM skills WHERE name = ?", (name,))
            conn.commit()
        logger.info(f"Skill deleted: {name}")
        return True
    except Exception as e:
        logger.exception(f"Error deleting skill {name}: {e}")
        return False

def list_skills() -> List[SkillMeta]:
    """List all skills in the database.
    
    Returns:
        List of SkillMeta objects
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT name, description, version, inputs FROM skills"
            )
            rows = cursor.fetchall()
            
            # Convert rows to SkillMeta objects
            skills = []
            for row in rows:
                meta = SkillMeta(
                    name=row["name"],
                    description=row["description"],
                    version=row["version"],
                    inputs=json.loads(row["inputs"]),
                )
                skills.append(meta)
                
            return skills
    except Exception as e:
        logger.exception(f"Error listing skills: {e}")
        return []

# Session operations
def create_session(session: ChatSession) -> bool:
    """Create a new chat session.
    
    Args:
        session: Session data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            # Insert session
            conn.execute(
                """INSERT INTO sessions 
                (id, name, created_at, updated_at) 
                VALUES (?, ?, ?, ?)""",
                (
                    session.id,
                    session.name,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                ),
            )
            
            # Insert messages
            for msg in session.messages:
                conn.execute(
                    """INSERT INTO messages 
                    (id, session_id, role, content, timestamp, skill_generated) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        msg.id,
                        msg.session_id,
                        msg.role,
                        msg.content,
                        msg.timestamp.isoformat(),
                        msg.skill_generated,
                    ),
                )
                
            conn.commit()
        logger.info(f"Session created: {session.id}")
        return True
    except Exception as e:
        logger.exception(f"Error creating session {session.id}: {e}")
        return False

def get_session(session_id: str) -> Optional[ChatSession]:
    """Get a chat session by ID.
    
    Args:
        session_id: Session ID
        
    Returns:
        ChatSession if found, None otherwise
    """
    try:
        with get_db_connection() as conn:
            # Get session
            cursor = conn.execute(
                "SELECT id, name, created_at, updated_at FROM sessions WHERE id = ?",
                (session_id,),
            )
            session_row = cursor.fetchone()
            
            if not session_row:
                return None
                
            # Get messages for this session
            msg_cursor = conn.execute(
                """SELECT id, session_id, role, content, timestamp, skill_generated 
                FROM messages 
                WHERE session_id = ? 
                ORDER BY timestamp""",
                (session_id,),
            )
            msg_rows = msg_cursor.fetchall()
            
            # Create messages
            messages = []
            for row in msg_rows:
                message = ChatMessage(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    skill_generated=row["skill_generated"],
                )
                messages.append(message)
            
            # Create session with messages
            session = ChatSession(
                id=session_row["id"],
                name=session_row["name"],
                created_at=datetime.fromisoformat(session_row["created_at"]),
                updated_at=datetime.fromisoformat(session_row["updated_at"]),
                messages=messages,
            )
            
            return session
    except Exception as e:
        logger.exception(f"Error getting session {session_id}: {e}")
        return None

def list_sessions() -> List[ChatSession]:
    """List all chat sessions.
    
    Returns:
        List of ChatSession objects
    """
    try:
        with get_db_connection() as conn:
            # Get all sessions
            cursor = conn.execute(
                "SELECT id, name, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
            )
            session_rows = cursor.fetchall()
            
            # Create sessions
            sessions = []
            for row in session_rows:
                session_id = row["id"]
                
                # Get messages for this session
                msg_cursor = conn.execute(
                    """SELECT id, session_id, role, content, timestamp, skill_generated 
                    FROM messages 
                    WHERE session_id = ? 
                    ORDER BY timestamp""",
                    (session_id,),
                )
                msg_rows = msg_cursor.fetchall()
                
                # Create messages
                messages = []
                for msg_row in msg_rows:
                    message = ChatMessage(
                        id=msg_row["id"],
                        session_id=msg_row["session_id"],
                        role=msg_row["role"],
                        content=msg_row["content"],
                        timestamp=datetime.fromisoformat(msg_row["timestamp"]),
                        skill_generated=msg_row["skill_generated"],
                    )
                    messages.append(message)
                
                # Create session with messages
                session = ChatSession(
                    id=row["id"],
                    name=row["name"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    messages=messages,
                )
                sessions.append(session)
                
            return sessions
    except Exception as e:
        logger.exception(f"Error listing sessions: {e}")
        return []

def add_message(message: ChatMessage) -> bool:
    """Add a message to a chat session.
    
    Args:
        message: Message data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            # Insert message
            conn.execute(
                """INSERT INTO messages 
                (id, session_id, role, content, timestamp, skill_generated) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    message.id,
                    message.session_id,
                    message.role,
                    message.content,
                    message.timestamp.isoformat(),
                    message.skill_generated,
                ),
            )
            
            # Update session updated_at timestamp
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), message.session_id),
            )
            
            conn.commit()
        logger.info(f"Message added to session {message.session_id}")
        return True
    except Exception as e:
        logger.exception(f"Error adding message to session {message.session_id}: {e}")
        return False

def delete_session(session_id: str) -> bool:
    """Delete a chat session.
    
    Args:
        session_id: Session ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            # Delete session (will cascade to messages)
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
        logger.info(f"Session deleted: {session_id}")
        return True
    except Exception as e:
        logger.exception(f"Error deleting session {session_id}: {e}")
        return False
