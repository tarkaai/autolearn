"""FastAPI endpoints for the Consumer Agent."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from .consumer_agent import ConsumerAgent, get_consumer_agent, ConversationContext, SkillSuggestion

logger = logging.getLogger("autolearn.consumer_agent_endpoints")

# Create router for consumer agent endpoints
router = APIRouter(prefix="/consumer-agent", tags=["consumer-agent"])


class ChatRequest(BaseModel):
    """Request for consumer agent chat."""
    
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID (will create new if not provided)")


class ChatResponse(BaseModel):
    """Response from consumer agent chat."""
    
    message: str = Field(..., description="Agent response message")
    session_id: str = Field(..., description="Session ID")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Actions taken by agent")
    suggestions: List[SkillSuggestion] = Field(default_factory=list, description="Skill suggestions")
    needs_skill_generation: bool = Field(False, description="Whether new skill generation is needed")


class SkillSuggestionsRequest(BaseModel):
    """Request for skill suggestions."""
    
    query: str = Field(..., description="User query to get suggestions for")
    session_id: Optional[str] = Field(None, description="Session ID for context")


class SkillSuggestionsResponse(BaseModel):
    """Response with skill suggestions."""
    
    suggestions: List[SkillSuggestion] = Field(..., description="List of skill suggestions")


class SkillGenerationRequest(BaseModel):
    """Request to generate a new skill."""
    
    description: str = Field(..., description="Description of the skill to generate")
    name: Optional[str] = Field(None, description="Optional name for the skill")
    session_id: str = Field(..., description="Session ID for context")


class SkillGenerationResponse(BaseModel):
    """Response from skill generation."""
    
    success: bool = Field(..., description="Whether generation was successful")
    message: str = Field(..., description="Status message")
    skill: Optional[Dict[str, Any]] = Field(None, description="Generated skill information")
    error: Optional[str] = Field(None, description="Error message if failed")


class ConversationHistoryResponse(BaseModel):
    """Response with conversation history."""
    
    session_id: str = Field(..., description="Session ID")
    messages: List[Dict[str, Any]] = Field(..., description="Conversation messages")
    skills_used: List[str] = Field(..., description="Skills used in conversation")
    skills_requested: List[str] = Field(..., description="Skills requested for generation")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    agent: ConsumerAgent = Depends(get_consumer_agent)
) -> ChatResponse:
    """Send a message to the consumer agent and get a response."""
    
    try:
        # Start new session if none provided
        session_id = request.session_id
        if not session_id:
            session_id = await agent.start_conversation()
            
        # Process the chat message
        result = await agent.chat(session_id, request.message)
        
        return ChatResponse(
            message=result["message"],
            session_id=result.get("session_id", session_id),
            actions=result.get("actions", []),
            suggestions=result.get("suggestions", []),
            needs_skill_generation=result.get("needs_skill_generation", False)
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.get("/skills/suggestions", response_model=SkillSuggestionsResponse)
async def get_skill_suggestions(
    query: str,
    session_id: Optional[str] = None,
    agent: ConsumerAgent = Depends(get_consumer_agent)
) -> SkillSuggestionsResponse:
    """Get skill suggestions based on user query."""
    
    try:
        # For now, we'll use the MCP client to get available tools and suggest from those
        from .consumer_agent import MCPClient
        
        async with MCPClient(agent.mcp_server_url) as mcp:
            available_tools = await mcp.list_tools()
            suggestions = await agent._get_skill_suggestions(query, available_tools)
            
        return SkillSuggestionsResponse(suggestions=suggestions)
        
    except Exception as e:
        logger.error(f"Skill suggestions error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/skills/available")
async def get_available_skills(
    agent: ConsumerAgent = Depends(get_consumer_agent)
) -> Dict[str, Any]:
    """Get list of skills available via MCP."""
    
    try:
        from .consumer_agent import MCPClient
        
        async with MCPClient(agent.mcp_server_url) as mcp:
            tools = await mcp.list_tools()
            
        return {
            "tools": tools,
            "count": len(tools),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Available skills error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available skills: {str(e)}")


@router.post("/skills/execute")
async def execute_skill(
    skill_name: str,
    arguments: Dict[str, Any],
    session_id: Optional[str] = None,
    agent: ConsumerAgent = Depends(get_consumer_agent)
) -> Dict[str, Any]:
    """Execute a skill through MCP protocol."""
    
    try:
        from .consumer_agent import MCPClient
        
        async with MCPClient(agent.mcp_server_url) as mcp:
            result = await mcp.call_tool(skill_name, arguments)
            
        # Update conversation context if session provided
        if session_id and session_id in agent.conversations:
            context = agent.conversations[session_id]
            if skill_name not in context.skills_used:
                context.skills_used.append(skill_name)
                
        return {
            "success": True,
            "result": result,
            "skill_name": skill_name,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Skill execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Skill execution failed: {str(e)}")


@router.post("/skills/request", response_model=SkillGenerationResponse)
async def request_skill_generation(
    request: SkillGenerationRequest,
    agent: ConsumerAgent = Depends(get_consumer_agent)
) -> SkillGenerationResponse:
    """Request generation of a new skill."""
    
    try:
        result = await agent.request_skill_generation(
            request.session_id,
            request.description,
            request.name
        )
        
        return SkillGenerationResponse(**result)
        
    except Exception as e:
        logger.error(f"Skill generation request error: {e}")
        raise HTTPException(status_code=500, detail=f"Skill generation request failed: {str(e)}")


@router.get("/conversation/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    agent: ConsumerAgent = Depends(get_consumer_agent)
) -> ConversationHistoryResponse:
    """Get conversation history for a session."""
    
    context = agent.get_conversation_history(session_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Convert messages to dict format
    messages = []
    for msg in context.messages:
        messages.append({
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "metadata": msg.metadata
        })
        
    return ConversationHistoryResponse(
        session_id=context.session_id,
        messages=messages,
        skills_used=context.skills_used,
        skills_requested=context.skills_requested
    )


@router.get("/reasoning/{session_id}")
async def get_agent_reasoning(
    session_id: str,
    agent: ConsumerAgent = Depends(get_consumer_agent)
) -> Dict[str, Any]:
    """Get agent reasoning traces for a session."""
    
    context = agent.get_conversation_history(session_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Extract reasoning information from conversation
    reasoning_traces = []
    for msg in context.messages:
        if msg.role == "assistant" and msg.metadata:
            reasoning_traces.append({
                "timestamp": msg.timestamp.isoformat(),
                "content": msg.content,
                "metadata": msg.metadata
            })
            
    return {
        "session_id": session_id,
        "reasoning_traces": reasoning_traces,
        "skills_used": context.skills_used,
        "skills_requested": context.skills_requested
    }


@router.post("/sessions/start")
async def start_new_session(
    user_id: str = "default",
    agent: ConsumerAgent = Depends(get_consumer_agent)
) -> Dict[str, Any]:
    """Start a new conversation session."""
    
    try:
        session_id = await agent.start_conversation(user_id)
        
        return {
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
    except Exception as e:
        logger.error(f"Session start error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")
