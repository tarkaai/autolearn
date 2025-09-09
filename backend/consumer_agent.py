"""AI Consumer Agent that uses MCP to connect to AutoLearn server.

This agent serves as an intelligent intermediary between users and the AutoLearn
MCP server, providing natural language interaction and automatic skill generation.
"""

from __future__ import annotations

import json
import logging
import os
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

import httpx
from openai import OpenAI

from .openai_client import OpenAIClient, OpenAIConfig
from .schemas import SkillMeta

logger = logging.getLogger("autolearn.consumer_agent")


class ConversationMessage(BaseModel):
    """A message in the conversation history."""
    
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")


class ConversationContext(BaseModel):
    """Conversation context and memory for the consumer agent."""
    
    session_id: str = Field(..., description="Unique session identifier")
    messages: List[ConversationMessage] = Field(default_factory=list)
    skills_used: List[str] = Field(default_factory=list, description="Skills used in this conversation")
    skills_requested: List[str] = Field(default_factory=list, description="Skills requested for generation")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences and context")


class SkillSuggestion(BaseModel):
    """A skill suggestion for the user."""
    
    skill_name: str = Field(..., description="Name of the suggested skill")
    description: str = Field(..., description="Description of what the skill does")
    relevance_score: float = Field(..., description="Relevance score (0.0-1.0)")
    reason: str = Field(..., description="Why this skill is suggested")


class MCPClient:
    """JSON-RPC 2.0 client for communicating with AutoLearn MCP server."""
    
    def __init__(self, server_url: str = "http://localhost:8000/mcp"):
        self.server_url = server_url
        self.session = httpx.AsyncClient()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
        
    async def call_method(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a JSON-RPC 2.0 call to the MCP server."""
        
        request_id = f"req_{datetime.now().timestamp()}"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        try:
            response = await self.session.post(
                self.server_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "error" in result:
                raise Exception(f"MCP Error: {result['error']}")
                
            return result.get("result")
            
        except httpx.RequestError as e:
            logger.error(f"MCP request failed: {e}")
            raise Exception(f"Failed to connect to MCP server: {e}")
            
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server."""
        result = await self.call_method("tools/list")
        return result.get("tools", [])
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool via MCP server."""
        return await self.call_method("tools/call", {
            "name": name,
            "arguments": arguments
        })


class ConsumerAgent:
    """AI Consumer Agent that provides intelligent MCP client functionality."""
    
    def __init__(
        self, 
        openai_client: Optional[OpenAIClient] = None,
        mcp_server_url: str = "http://localhost:8000/mcp"
    ):
        self.openai_client = openai_client or self._create_default_openai_client()
        self.mcp_server_url = mcp_server_url
        self.conversations: Dict[str, ConversationContext] = {}
        
    def _create_default_openai_client(self) -> OpenAIClient:
        """Create default OpenAI client for the agent."""
        config = OpenAIConfig(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model_name="gpt-4o",
            temperature=0.3  # Slightly higher for conversation
        )
        return OpenAIClient(config)
        
    async def start_conversation(self, user_id: str = "default") -> str:
        """Start a new conversation session."""
        session_id = f"{user_id}_{datetime.now().timestamp()}"
        
        context = ConversationContext(
            session_id=session_id,
            messages=[
                ConversationMessage(
                    role="system",
                    content="""You are an AI assistant that helps users by using and creating skills through the AutoLearn MCP server. 

Your capabilities include:
1. Using existing skills to help users with their tasks
2. Identifying when new skills need to be created
3. Requesting skill generation from the AutoLearn server
4. Providing natural, helpful responses while managing skills intelligently

When a user asks for something you can't do with existing skills, you should:
1. Explain what you're trying to do
2. Check if any existing skills might help
3. If not, request generation of a new skill
4. Use the newly created skill to help the user

Always be helpful, clear, and transparent about what skills you're using or creating."""
                )
            ]
        )
        
        self.conversations[session_id] = context
        return session_id
        
    async def chat(
        self, 
        session_id: str, 
        user_message: str
    ) -> Dict[str, Any]:
        """Process a user message and return agent response with actions."""
        
        if session_id not in self.conversations:
            session_id = await self.start_conversation()
            
        context = self.conversations[session_id]
        
        # Add user message to context
        context.messages.append(ConversationMessage(
            role="user",
            content=user_message
        ))
        
        # Analyze user intent and determine actions
        async with MCPClient(self.mcp_server_url) as mcp:
            try:
                # Get available tools from MCP server
                available_tools = await mcp.list_tools()
                
                # Use OpenAI to determine response and actions
                response = await self._generate_response(
                    context, user_message, available_tools
                )
                
                # Add agent response to context
                context.messages.append(ConversationMessage(
                    role="assistant",
                    content=response["message"]
                ))
                
                return response
                
            except Exception as e:
                logger.error(f"Error in chat processing: {e}")
                error_response = {
                    "message": "I'm having trouble connecting to my skill system. Let me try to help you directly.",
                    "actions": [],
                    "suggestions": [],
                    "needs_skill_generation": False
                }
                
                context.messages.append(ConversationMessage(
                    role="assistant",
                    content=error_response["message"]
                ))
                
                return error_response
                
    async def _generate_response(
        self, 
        context: ConversationContext,
        user_message: str,
        available_tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate agent response using OpenAI with context about available tools."""
        
        # Create tool descriptions for the prompt
        tool_descriptions = []
        for tool in available_tools:
            tool_descriptions.append(f"- {tool['name']}: {tool.get('description', 'No description')}")
            
        tools_text = "\n".join(tool_descriptions) if tool_descriptions else "No tools available"
        
        # Create conversation history for OpenAI
        messages = []
        for msg in context.messages[-10:]:  # Last 10 messages for context
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
            
        # Add current analysis prompt
        analysis_prompt = f"""Available skills/tools:
{tools_text}

User message: {user_message}

Please analyze this request and respond with:
1. A helpful message to the user
2. Whether you can handle this with existing tools
3. If you need to create a new skill, what it should do
4. Any tool calls you want to make

Respond in a natural, conversational way while being clear about what actions you're taking."""

        messages.append({
            "role": "user", 
            "content": analysis_prompt
        })
        
        try:
            # Use OpenAI to generate response
            client = OpenAI(api_key=self.openai_client.config.api_key)
            
            completion = client.chat.completions.create(
                model=self.openai_client.config.model_name,
                messages=messages,
                temperature=self.openai_client.config.temperature,
                max_tokens=1000
            )
            
            agent_response = completion.choices[0].message.content
            
            # Parse response to determine actions
            # For now, simple keyword-based detection
            needs_skill_generation = any(keyword in agent_response.lower() for keyword in [
                "create a skill", "new skill", "generate a skill", "don't have a skill",
                "creation of a new skill", "request the creation", "none of the existing skills",
                "creating this new skill", "i'll request the creation", "go ahead and request"
            ])
            
            # Suggest relevant existing tools
            suggestions = await self._get_skill_suggestions(user_message, available_tools)
            
            actions = []
            
            # If skill generation is needed, attempt to generate it automatically
            if needs_skill_generation:
                logger.info(f"Skill generation needed for message: {user_message}")
                try:
                    # Extract skill description from user message and agent response
                    skill_description = self._extract_skill_description(user_message, agent_response)
                    logger.info(f"Extracted skill description: {skill_description}")
                    
                    # Generate the skill
                    generation_result = await self.request_skill_generation(
                        context.session_id, 
                        skill_description
                    )
                    
                    logger.info(f"Skill generation result: {generation_result}")
                    
                    if generation_result["success"]:
                        actions.append({
                            "type": "skill_generated",
                            "skill": generation_result["skill"],
                            "skill_name": generation_result["skill"].get("name", "unnamed"),
                            "description": skill_description
                        })
                        
                        # Update agent response to include success message
                        agent_response = f"{agent_response}\n\n🎉 Great news! I've successfully created a new skill called '{generation_result['skill'].get('name', 'unnamed')}' that can help you with this task!"
                        
                        # Mark skill as used since we generated it for this request
                        skill_name = generation_result["skill"].get("name", "unnamed")
                        context.skills_used.append(skill_name)
                        actions.append({
                            "type": "skill_used",
                            "skill_name": skill_name
                        })
                        
                except Exception as e:
                    logger.error(f"Auto skill generation failed: {e}")
                    # Keep the original response indicating we'll create the skill
            else:
                logger.info(f"No skill generation needed. Response: {agent_response[:100]}...")
            
            return {
                "message": agent_response,
                "actions": actions,
                "suggestions": suggestions,
                "needs_skill_generation": needs_skill_generation and len(actions) == 0,  # False if we successfully generated
                "session_id": context.session_id
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                "message": "I'm having trouble processing your request right now. Could you try rephrasing it?",
                "actions": [],
                "suggestions": [],
                "needs_skill_generation": False
            }
            
    def _extract_skill_description(self, user_message: str, agent_response: str) -> str:
        """Extract a skill description from user message and agent response."""
        # Simple extraction - look for common patterns
        user_lower = user_message.lower()
        
        # Look for "create a skill to..." or "help me..." patterns
        if "create a skill to" in user_lower:
            # Extract everything after "create a skill to"
            start_idx = user_lower.find("create a skill to") + len("create a skill to")
            description = user_message[start_idx:].strip()
            if description:
                return description
        
        if "help me" in user_lower:
            # Extract everything after "help me"
            start_idx = user_lower.find("help me") + len("help me")
            description = user_message[start_idx:].strip()
            if description:
                return f"Help with: {description}"
        
        # Fallback: use the entire user message
        return user_message
    
    async def _get_skill_suggestions(
        self, 
        user_message: str, 
        available_tools: List[Dict[str, Any]]
    ) -> List[SkillSuggestion]:
        """Get skill suggestions based on user message and available tools."""
        
        suggestions = []
        user_lower = user_message.lower()
        
        for tool in available_tools:
            name = tool.get("name", "")
            description = tool.get("description", "")
            
            # Simple relevance scoring based on keyword matching
            relevance = 0.0
            words = user_lower.split()
            
            for word in words:
                if word in name.lower():
                    relevance += 0.3
                if word in description.lower():
                    relevance += 0.2
                    
            if relevance > 0.1:  # Only suggest if somewhat relevant
                suggestions.append(SkillSuggestion(
                    skill_name=name,
                    description=description,
                    relevance_score=min(relevance, 1.0),
                    reason=f"Matches keywords from your request"
                ))
                
        # Sort by relevance and return top 3
        suggestions.sort(key=lambda x: x.relevance_score, reverse=True)
        return suggestions[:3]
        
    async def request_skill_generation(
        self, 
        session_id: str, 
        skill_description: str,
        skill_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Request generation of a new skill from AutoLearn server."""
        
        try:
            # Use the REST API directly for skill generation
            from .openai_client import get_openai_client
            from .schemas import GenerateSkillRequest
            
            # Get the configured OpenAI client and generation request
            openai_client = get_openai_client()
            generation_req = GenerateSkillRequest(
                description=skill_description,
                name=skill_name
            )
            
            # Generate the skill code
            result = openai_client.generate_skill_code(generation_req)
            
            if result and result.code and result.meta:
                # Register the skill with the engine
                from .skill_engine import get_engine
                from .schemas import SkillMeta
                engine = get_engine()
                
                # Convert meta dict to SkillMeta object (following the pattern from app.py)
                meta_dict = result.meta
                if not isinstance(meta_dict, dict):
                    raise ValueError("Generated metadata is not a dictionary")
                    
                skill_meta = SkillMeta(
                    name=meta_dict.get("name", skill_name or "unnamed_skill"),
                    description=meta_dict.get("description", skill_description),
                    version=meta_dict.get("version", "0.1.0"),
                    inputs=meta_dict.get("inputs", {})
                )
                
                # Register the generated skill
                engine.register_from_code(result.code, skill_meta)
                
                # Registration succeeded if we get here without exception
                # Update conversation context
                if session_id in self.conversations:
                    context = self.conversations[session_id]
                    context.skills_requested.append(skill_name or skill_description)
                    
                return {
                    "success": True,
                    "skill": {
                        "name": skill_meta.name,
                        "description": skill_meta.description,
                        "version": skill_meta.version,
                        "code": result.code
                    },
                    "message": f"Successfully generated skill: {skill_meta.name}"
                }
            else:
                raise Exception("Skill generation returned invalid result")
                
        except Exception as e:
            logger.error(f"Skill generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "I wasn't able to generate that skill right now. Please try again."
            }
                
    def get_conversation_history(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation history for a session."""
        return self.conversations.get(session_id)


# Singleton instance for the app
_consumer_agent: Optional[ConsumerAgent] = None


def create_default_consumer_agent() -> ConsumerAgent:
    """Create default consumer agent instance."""
    return ConsumerAgent()


def get_consumer_agent() -> ConsumerAgent:
    """Get the global consumer agent instance."""
    global _consumer_agent
    if _consumer_agent is None:
        _consumer_agent = create_default_consumer_agent()
    return _consumer_agent
