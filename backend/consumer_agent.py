"""AI Consumer Agent that uses MCP to connect to AutoLearn server.

This agent serves as an intelligent intermediary between users and the AutoLearn
MCP server, providing natural language interaction and automatic skill generation.
"""

from __future__ import annotations

import json
import logging
import os
import asyncio
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

import httpx
from openai import OpenAI

from .openai_client import OpenAIClient, OpenAIConfig
from .schemas import SkillMeta, ChatSession, ChatMessage, CreateSessionRequest
from . import db, sessions

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
        self.initialized = False
        self.server_capabilities = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize MCP connection with the server."""
        if self.initialized:
            return {"status": "already_initialized"}
        
        init_params = {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {}  # Client supports tools
            },
            "clientInfo": {
                "name": "AutoLearn-ConsumerAgent",
                "version": "0.1.0"
            }
        }
        
        try:
            result = await self.call_method("initialize", init_params)
            
            if result:
                self.initialized = True
                self.server_capabilities = result.get("capabilities", {})
                logger.info(f"MCP client initialized. Server capabilities: {self.server_capabilities}")
                return result
            else:
                raise Exception("MCP initialization failed - no result returned")
                
        except Exception as e:
            logger.error(f"MCP initialization failed: {e}")
            raise Exception(f"Failed to initialize MCP connection: {e}")
        
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
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Handle MCP protocol errors
            if "error" in result:
                error_info = result["error"]
                error_code = error_info.get("code", -32603)
                error_message = error_info.get("message", "Unknown MCP error")
                
                logger.error(f"MCP Error {error_code}: {error_message}")
                
                # Map common MCP error codes to user-friendly messages
                if error_code == -32601:  # Method not found
                    raise Exception(f"MCP method '{method}' not supported by server")
                elif error_code == -32602:  # Invalid params
                    raise Exception(f"Invalid parameters for MCP method '{method}': {error_message}")
                elif error_code == -32603:  # Internal error
                    raise Exception(f"Server error in MCP method '{method}': {error_message}")
                else:
                    raise Exception(f"MCP Error {error_code}: {error_message}")
                
            return result.get("result")
            
        except httpx.TimeoutException:
            logger.error(f"MCP request timed out for method: {method}")
            raise Exception(f"Request to MCP server timed out")
        except httpx.ConnectError:
            logger.error(f"Failed to connect to MCP server at {self.server_url}")
            raise Exception(f"Unable to connect to MCP server at {self.server_url}")
        except httpx.RequestError as e:
            logger.error(f"MCP request failed: {e}")
            raise Exception(f"Network error connecting to MCP server: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from MCP server: {e}")
            raise Exception("Invalid response format from MCP server")
        except Exception as e:
            logger.error(f"Unexpected error in MCP request: {e}")
            raise
            
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server."""
        if not self.initialized:
            await self.initialize()
        result = await self.call_method("tools/list")
        return result.get("tools", [])
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool via MCP server."""
        if not self.initialized:
            await self.initialize()
        # Convert complex parameters to JSON strings for portability
        serialized_args = self._serialize_parameters(arguments)
        return await self.call_method("tools/call", {
            "name": name,
            "arguments": serialized_args
        })
    
    def _serialize_parameters(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize complex parameters to JSON strings for MCP portability."""
        import json
        serialized = {}
        
        for key, value in arguments.items():
            if isinstance(value, (dict, list)):
                # Convert complex types to JSON strings
                serialized[key] = json.dumps(value)
            else:
                # Keep simple types as-is
                serialized[key] = value
                
        return serialized
    
    def convert_mcp_tools_to_openai_functions(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tool schemas to OpenAI function definitions."""
        openai_functions = []
        
        for tool in mcp_tools:
            # Get the input schema and clean it up
            input_schema = tool.get("inputSchema", {
                "type": "object",
                "properties": {},
                "required": []
            })
            
            # Clean up invalid type values for OpenAI
            if "properties" in input_schema:
                for prop_name, prop_def in input_schema["properties"].items():
                    if isinstance(prop_def, dict) and "type" in prop_def:
                        # Replace invalid types with valid ones
                        if prop_def["type"] in ["any", "str"]:
                            prop_def["type"] = "string"
                        elif prop_def["type"] == "number":
                            prop_def["type"] = "number"
                        elif prop_def["type"] == "int":
                            prop_def["type"] = "integer"
                        elif prop_def["type"] == "bool":
                            prop_def["type"] = "boolean"
            
            # Convert MCP tool to OpenAI function format
            function_def = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": input_schema
                }
            }
            openai_functions.append(function_def)
            
        return openai_functions


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
        # Create a database session
        session_request = CreateSessionRequest(name=f"AutoLearn Chat - {user_id}")
        db_session = sessions.create_session(session_request)
        session_id = db_session.id
        
        # Also create in-memory context for immediate use
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
        user_msg = ConversationMessage(
            role="user",
            content=user_message
        )
        context.messages.append(user_msg)
        
        # Save user message to database
        try:
            from .schemas import AddMessageRequest
            db.add_message(ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                content=user_message,
                timestamp=user_msg.timestamp
            ))
        except Exception as e:
            logger.error(f"Error saving user message to database: {e}")
        
        # Analyze user intent and determine actions
        async with MCPClient(self.mcp_server_url) as mcp:
            try:
                logger.info(f"Starting MCP client with server URL: {self.mcp_server_url}")
                
                # Get available tools from MCP server
                available_tools = await mcp.list_tools()
                logger.info(f"Retrieved {len(available_tools)} tools from MCP server")
                
                # Convert MCP tools to OpenAI function definitions
                openai_functions = mcp.convert_mcp_tools_to_openai_functions(available_tools)
                logger.info(f"Converted to {len(openai_functions)} OpenAI function definitions")
                
                # Use OpenAI with function calling to determine response and actions
                # Fall back to old approach if no API key is available
                if self.openai_client.config.api_key:
                    try:
                        response = await self._generate_response_with_functions(
                            context, user_message, openai_functions, mcp
                        )
                    except Exception as e:
                        logger.warning(f"Function calling failed, falling back to old approach: {e}")
                        response = await self._generate_response(
                            context, user_message, available_tools
                        )
                else:
                    logger.info("No OpenAI API key available, using old approach")
                    response = await self._generate_response(
                        context, user_message, available_tools
                    )
                
                # Add agent response to context
                assistant_msg = ConversationMessage(
                    role="assistant",
                    content=response["message"]
                )
                context.messages.append(assistant_msg)
                
                # Save assistant message to database
                try:
                    db.add_message(ChatMessage(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        role="assistant",
                        content=response["message"],
                        timestamp=assistant_msg.timestamp
                    ))
                except Exception as e:
                    logger.error(f"Error saving assistant message to database: {e}")
                
                return response
                
            except Exception as e:
                logger.error(f"Error in chat processing: {e}")
                error_response = {
                    "message": "I'm having trouble connecting to my skill system. Let me try to help you directly.",
                    "actions": [],
                    "suggestions": [],
                    "needs_skill_generation": False
                }
                
                error_msg = ConversationMessage(
                    role="assistant",
                    content=error_response["message"]
                )
                context.messages.append(error_msg)
                
                # Save error message to database
                try:
                    db.add_message(ChatMessage(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        role="assistant",
                        content=error_response["message"],
                        timestamp=error_msg.timestamp
                    ))
                except Exception as e:
                    logger.error(f"Error saving error message to database: {e}")
                
                return error_response
                
    async def _generate_response_with_functions(
        self, 
        context: ConversationContext,
        user_message: str,
        openai_functions: List[Dict[str, Any]],
        mcp_client: MCPClient
    ) -> Dict[str, Any]:
        """Generate agent response using OpenAI function calling with MCP tools."""
        
        # Create conversation history for OpenAI
        messages = []
        for msg in context.messages[-10:]:  # Last 10 messages for context
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            # Use OpenAI with function calling
            client = OpenAI(api_key=self.openai_client.config.api_key)
            
            completion = client.chat.completions.create(
                model=self.openai_client.config.model_name,
                messages=messages,
                tools=openai_functions if openai_functions else None,
                tool_choice="auto" if openai_functions else None,
                temperature=self.openai_client.config.temperature,
                max_tokens=1000,
                timeout=30
            )
            
            assistant_message = completion.choices[0].message
            
            # Handle function calls if any
            actions = []
            if assistant_message.tool_calls:
                logger.info(f"OpenAI generated {len(assistant_message.tool_calls)} function calls")
                
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Executing function: {function_name} with args: {function_args}")
                    
                    try:
                        # Execute the function via MCP
                        result = await mcp_client.call_tool(function_name, function_args)
                        
                        # Extract the actual result value
                        clean_result = self._extract_result_value(result)
                        
                        # Check if the result indicates an error
                        if isinstance(clean_result, str) and clean_result.startswith("Error:"):
                            raise Exception(clean_result)
                        
                        action = {
                            "type": "skill_used",
                            "skill_name": function_name,
                            "result": clean_result,
                            "raw_result": result,
                            "inputs": function_args
                        }
                        actions.append(action)
                        
                        # Add tool result to conversation for follow-up
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(clean_result)
                        })
                        
                        # Update context
                        context.skills_used.append(function_name)
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error executing function {function_name}: {error_msg}")
                        
                        action = {
                            "type": "skill_error",
                            "skill_name": function_name,
                            "error": error_msg,
                            "inputs": function_args
                        }
                        actions.append(action)
                        
                        # Add error to conversation with more context
                        error_content = f"Error executing {function_name}: {error_msg}"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": error_content
                        })
                
                # Get final response after function execution
                if messages:  # If we added tool results
                    final_completion = client.chat.completions.create(
                        model=self.openai_client.config.model_name,
                        messages=messages,
                        temperature=self.openai_client.config.temperature,
                        max_tokens=500,
                        timeout=15
                    )
                    assistant_message = final_completion.choices[0].message
            
            # Get the final message content
            agent_response = assistant_message.content or "I've executed the requested actions."
            
            # Get skill suggestions
            suggestions = await self._get_skill_suggestions(user_message, 
                [{"name": f["function"]["name"], "description": f["function"]["description"]} 
                 for f in openai_functions])
            
            return {
                "message": agent_response,
                "actions": actions,
                "suggestions": suggestions,
                "needs_skill_generation": False,  # Function calling handles this automatically
                "session_id": context.session_id
            }
            
        except Exception as e:
            logger.error(f"OpenAI function calling error: {e}")
            # Fall back to old approach
            logger.info("Falling back to old analysis approach")
            # Get available tools from MCP client for fallback
            try:
                available_tools = await mcp_client.list_tools()
                return await self._generate_response(
                    context, user_message, available_tools
                )
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return {
                    "message": "I'm having trouble processing your request right now. Could you try rephrasing it?",
                    "actions": [],
                    "suggestions": [],
                    "needs_skill_generation": False
                }

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
            
        # Add current analysis prompt with simplified context awareness
        context_hint = ""
        if len(context.messages) > 1:
            last_msg = context.messages[-2]  # Previous message
            if last_msg.role == "assistant" and ("fibonacci" in last_msg.content.lower() or "sequence" in last_msg.content.lower()):
                if user_message.strip().startswith("to ") or user_message.isdigit():
                    context_hint = f"\nCONTEXT: User previously asked about fibonacci sequence. Current message '{user_message}' likely specifies number of terms."

        analysis_prompt = f"""Available skills/tools:
{tools_text}

User message: {user_message}{context_hint}

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
                max_tokens=500,
                timeout=15
            )
            
            agent_response = completion.choices[0].message.content
            
            # Suggest relevant existing tools
            suggestions = await self._get_skill_suggestions(user_message, available_tools)
            
            actions = []
            
            # First, try to execute existing tools that can handle the request
            executed_tools = await self._try_execute_relevant_tools(
                user_message, agent_response, available_tools, context
            )
            
            if executed_tools:
                # Add tool execution actions
                actions.extend(executed_tools)
                # Update the response to include results and parameter correction info
                for tool_result in executed_tools:
                    # Add parameter correction feedback if present
                    if "parameter_corrections" in tool_result:
                        corrections = tool_result["parameter_corrections"]
                        if corrections.get("successful_correction"):
                            original_param = corrections.get("problem_parameter", "parameter")
                            corrected_param = corrections["successful_correction"]
                            agent_response += f"\n\n🔧 **Parameter Correction**: I noticed the skill expected '{corrected_param}' instead of '{original_param}', so I corrected that for you."
                        elif corrections.get("corrections_attempted"):
                            agent_response += f"\n\n⚠️ **Parameter Issue**: I tried to correct some parameter names but the skill still had issues."
                    
                    if tool_result.get("result") is not None:
                        result_value = tool_result['result']
                        # Check if result contains an error
                        if isinstance(result_value, str) and result_value.startswith("Error:"):
                            agent_response += f"\n\n❌ **Error**: {result_value}"
                            # Add user-friendly explanation for common errors
                            if "unexpected keyword argument" in result_value:
                                agent_response += "\n\n💡 This seems to be a parameter mismatch issue. The skill might need an update to handle your request better."
                        else:
                            agent_response += f"\n\n✅ **Result**: {result_value}"
            
            # Handle cases where AI analysis suggests creating or improving skills
            else:
                # Re-get the analysis to check what the AI recommended
                analysis = await self._analyze_skill_requirements(user_message, available_tools, context)
                
                if analysis.get("action") == "create":
                    logger.info(f"AI recommends creating new skill for: {user_message}")
                    try:
                        new_skill_info = analysis.get("new_skill", {})
                        skill_name = new_skill_info.get("name", "")
                        skill_description = new_skill_info.get("description", "")
                        uses_existing = new_skill_info.get("uses_existing_skills", [])
                        rationale = new_skill_info.get("rationale", "")
                        
                        # Create enhanced skill description that includes using existing skills
                        enhanced_description = skill_description
                        if uses_existing:
                            enhanced_description += f"\n\nThis skill should utilize these existing skills: {', '.join(uses_existing)}"
                            enhanced_description += f"\n\nRationale: {rationale}"
                        
                        # Generate the skill
                        generation_result = await self.request_skill_generation(
                            context.session_id, 
                            enhanced_description,
                            skill_name,
                            available_tools
                        )
                        
                        logger.info(f"Skill generation result: {generation_result}")
                        
                        if generation_result["success"]:
                            actions.append({
                                "type": "skill_generated",
                                "skill": generation_result["skill"],
                                "skill_name": generation_result["skill"].get("name", skill_name),
                                "description": enhanced_description,
                                "uses_existing_skills": uses_existing,
                                "ai_reasoning": analysis.get("reasoning", "")
                            })
                            
                            # Update agent response to include success message
                            skill_display_name = generation_result["skill"].get("name", skill_name)
                            agent_response = f"{agent_response}\n\n🎉 I've created a new skill called '{skill_display_name}' that can help you with this task!"
                            
                            if uses_existing:
                                agent_response += f" This skill leverages existing capabilities: {', '.join(uses_existing)}."
                            
                            # Mark skill as used since we generated it for this request
                            context.skills_used.append(skill_display_name)
                            actions.append({
                                "type": "skill_used",
                                "skill_name": skill_display_name
                            })
                            
                    except Exception as e:
                        logger.error(f"AI-driven skill generation failed: {e}")
                        
                elif analysis.get("action") == "improve":
                    logger.info(f"AI suggests improving existing skill for: {user_message}")
                    improvement_info = analysis.get("skill_to_improve", {})
                    
                    try:
                        # Actually execute the skill improvement
                        improvement_result = await self._execute_skill_improvement(
                            improvement_info.get("current_name"),
                            improvement_info.get("improvements"),
                            improvement_info.get("new_description")
                        )
                        
                        if improvement_result["success"]:
                            actions.append({
                                "type": "skill_improved",
                                "current_skill": improvement_info.get("current_name"),
                                "improvements": improvement_info.get("improvements"),
                                "new_description": improvement_info.get("new_description"),
                                "ai_reasoning": analysis.get("reasoning", ""),
                                "improvement_result": improvement_result
                            })
                            
                            agent_response += f"\n\n🔧 I've improved the '{improvement_info.get('current_name')}' skill to better handle your request! The improvements include: {improvement_info.get('improvements')}"
                            
                            # Mark skill as used since we improved it for this request
                            context.skills_used.append(improvement_info.get("current_name"))
                            actions.append({
                                "type": "skill_used",
                                "skill_name": improvement_info.get("current_name")
                            })
                        else:
                            # Fallback to suggestion if improvement fails
                            actions.append({
                                "type": "skill_improvement_suggested",
                                "current_skill": improvement_info.get("current_name"),
                                "improvements": improvement_info.get("improvements"),
                                "new_description": improvement_info.get("new_description"),
                                "ai_reasoning": analysis.get("reasoning", ""),
                                "improvement_error": improvement_result.get("error", "Unknown error")
                            })
                            
                            agent_response += f"\n\n💡 I notice that the existing '{improvement_info.get('current_name')}' skill could be improved to better handle your request. Suggested improvements: {improvement_info.get('improvements')}"
                            
                    except Exception as e:
                        logger.error(f"Skill improvement failed: {e}")
                        # Fallback to suggestion
                        actions.append({
                            "type": "skill_improvement_suggested",
                            "current_skill": improvement_info.get("current_name"),
                            "improvements": improvement_info.get("improvements"),
                            "new_description": improvement_info.get("new_description"),
                            "ai_reasoning": analysis.get("reasoning", ""),
                            "improvement_error": str(e)
                        })
                        
                        agent_response += f"\n\n💡 I notice that the existing '{improvement_info.get('current_name')}' skill could be improved to better handle your request. Suggested improvements: {improvement_info.get('improvements')}"
                    
                else:
                    logger.info(f"AI analysis complete. No additional actions needed.")
            
            needs_generation = len(actions) == 0 and any(keyword in user_message.lower() for keyword in [
                "create a skill", "new skill", "generate a skill", "make a skill"
            ])
            
            return {
                "message": agent_response,
                "actions": actions,
                "suggestions": suggestions,
                "needs_skill_generation": needs_generation,
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
            
    async def _analyze_skill_requirements(
        self,
        user_message: str,
        available_tools: List[Dict[str, Any]],
        context: Optional[ConversationContext] = None
    ) -> Dict[str, Any]:
        """Use OpenAI to analyze user request against available skills and determine action."""
        
        # Create a detailed description of available skills
        skills_description = []
        for tool in available_tools:
            skill_info = f"- {tool['name']}: {tool.get('description', 'No description')}"
            # Handle MCP format with inputSchema
            if 'inputSchema' in tool and 'properties' in tool['inputSchema']:
                params = tool['inputSchema']['properties']
                if params:
                    param_names = list(params.keys())
                    skill_info += f" (takes: {', '.join(param_names)})"
            skills_description.append(skill_info)
        
        skills_text = "\n".join(skills_description) if skills_description else "No skills available"
        
        # Add simplified conversation context if available
        context_info = ""
        if context and len(context.messages) > 1:
            last_msg = context.messages[-2]  # Previous message  
            if last_msg.role == "assistant":
                # Check for specific context patterns
                if "fibonacci" in last_msg.content.lower() and ("to " in user_message or user_message.isdigit()):
                    context_info = f"\nCONTEXT: Previous request was about fibonacci sequence. '{user_message}' likely specifies the number of terms."
                elif "calculate" in last_msg.content.lower() and any(c.isdigit() for c in user_message):
                    context_info = f"\nCONTEXT: Previous request was about calculation. '{user_message}' likely provides numbers/parameters."
        
        analysis_prompt = f"""You are an intelligent skill orchestrator. Analyze the user's request against available skills and determine the best action.

Available Skills:
{skills_text}{context_info}

User Request: "{user_message}"

Please analyze this request and respond with a JSON object containing your decision:

{{
  "action": "execute|improve|create",
  "reasoning": "brief explanation of your decision",
  "skill_to_execute": {{
    "name": "skill_name",
    "parameters": {{"param1": "value1", "param2": "value2"}}
  }},
  "skill_to_improve": {{
    "current_name": "existing_skill_name",
    "improvements": "what improvements are needed",
    "new_description": "improved skill description"
  }},
  "new_skill": {{
    "name": "proposed_skill_name",
    "description": "what the new skill should do",
    "uses_existing_skills": ["skill1", "skill2"],
    "rationale": "why a new skill is needed"
  }}
}}

Decision Guidelines:
1. Choose "execute" if an existing skill can directly handle the request
2. Choose "improve" if an existing skill is close but needs to be more general/better
3. Choose "create" if no existing skill can handle the request, but consider how the new skill could use existing ones

For "execute": Fill in skill_to_execute, leave others null
For "improve": Fill in skill_to_improve, leave others null  
For "create": Fill in new_skill, leave others null

CRITICAL: When using "execute", you MUST use the exact parameter names shown in parentheses after "(takes: ...)". 
IGNORE any parameter names mentioned in the skill description text - only use the names listed after "(takes: )".
For example, if a skill shows "(takes: num_terms, radius)" then use exactly: {{"num_terms": 10, "radius": 5}}.
Do NOT use parameter names from the description text, even if they seem similar.

Be intelligent about parameter extraction - if the user provides specific values, extract them for execution using the EXACT parameter names from the skill schema."""

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_client.config.api_key)
            
            completion = client.chat.completions.create(
                model=self.openai_client.config.model_name,
                messages=[{
                    "role": "user",
                    "content": analysis_prompt
                }],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=500,
                timeout=15
            )
            
            response_text = completion.choices[0].message.content
            
            # Try to parse the JSON response
            import json
            try:
                # Extract JSON from response (in case there's extra text)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    # Fallback if no JSON structure found
                    analysis = {"action": "create", "reasoning": "Could not parse analysis"}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse skill analysis JSON: {e}")
                logger.error(f"Raw response: {response_text}")
                # Fallback analysis
                analysis = {"action": "create", "reasoning": "JSON parsing failed"}
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in skill analysis: {e}")
            return {"action": "create", "reasoning": f"Analysis failed: {str(e)}"}

    async def _try_execute_relevant_tools(
        self, 
        user_message: str, 
        agent_response: str, 
        available_tools: List[Dict[str, Any]], 
        context: ConversationContext
    ) -> List[Dict[str, Any]]:
        """Use AI analysis to determine and execute relevant tools."""
        
        executed_actions = []
        
        # Get AI analysis of what should be done
        analysis = await self._analyze_skill_requirements(user_message, available_tools, context)
        logger.info(f"Skill analysis result: {analysis}")
        
        async with MCPClient(self.mcp_server_url) as mcp:
            try:
                if analysis.get("action") == "execute":
                    # Execute the recommended skill with intelligent parameter mapping and error recovery
                    skill_info = analysis.get("skill_to_execute", {})
                    skill_name = skill_info.get("name")
                    parameters = skill_info.get("parameters", {})
                    
                    if skill_name and any(tool["name"] == skill_name for tool in available_tools):
                        # Get the tool definition for parameter mapping
                        skill_tool = next((tool for tool in available_tools if tool["name"] == skill_name), None)
                        
                        # Apply intelligent parameter mapping
                        mapped_parameters = self._map_parameters_intelligently(
                            parameters, skill_tool, user_message
                        )
                        
                        logger.info(f"Executing skill: {skill_name} with params: {mapped_parameters}")
                        
                        # Execute with error recovery
                        result, retry_info = await self._execute_skill_with_retry(
                            mcp, skill_name, mapped_parameters, skill_tool
                        )
                        
                        clean_result = self._extract_result_value(result)
                        
                        action = {
                            "type": "skill_used",
                            "skill_name": skill_name,
                            "result": clean_result,
                            "raw_result": result,
                            "inputs": mapped_parameters,
                            "ai_reasoning": analysis.get("reasoning", "")
                        }
                        
                        # Add retry information if there was parameter correction
                        if retry_info:
                            action["parameter_corrections"] = retry_info
                        
                        executed_actions.append(action)
                        context.skills_used.append(skill_name)
                    else:
                        logger.warning(f"Recommended skill '{skill_name}' not found in available tools")
                
                elif analysis.get("action") == "improve":
                    # Execute skill improvement
                    improvement_info = analysis.get("skill_to_improve", {})
                    
                    try:
                        improvement_result = await self._execute_skill_improvement(
                            improvement_info.get("current_name"),
                            improvement_info.get("improvements"),
                            improvement_info.get("new_description")
                        )
                        
                        if improvement_result["success"]:
                            executed_actions.append({
                                "type": "skill_improved",
                                "current_skill": improvement_info.get("current_name"),
                                "improvements": improvement_info.get("improvements"),
                                "new_description": improvement_info.get("new_description"),
                                "ai_reasoning": analysis.get("reasoning", ""),
                                "improvement_result": improvement_result
                            })
                        else:
                            # Fallback to suggestion if improvement fails
                            executed_actions.append({
                                "type": "skill_improvement_suggested",
                                "current_skill": improvement_info.get("current_name"),
                                "improvements": improvement_info.get("improvements"),
                                "new_description": improvement_info.get("new_description"),
                                "ai_reasoning": analysis.get("reasoning", ""),
                                "improvement_error": improvement_result.get("error", "Unknown error")
                            })
                    except Exception as e:
                        logger.error(f"Skill improvement failed: {e}")
                        executed_actions.append({
                            "type": "skill_improvement_suggested",
                            "current_skill": improvement_info.get("current_name"),
                            "improvements": improvement_info.get("improvements"),
                            "new_description": improvement_info.get("new_description"),
                            "ai_reasoning": analysis.get("reasoning", ""),
                            "improvement_error": str(e)
                        })
                
                # For "create" action, we'll handle this in the calling function
                
            except Exception as e:
                logger.error(f"Error executing AI-recommended actions: {e}")
        
        return executed_actions
    
    async def _execute_skill_improvement(
        self,
        skill_name: str,
        improvements: str,
        new_description: str
    ) -> Dict[str, Any]:
        """Execute skill improvement by calling the improvement endpoint."""
        try:
            # Get current skill code from the MCP server
            async with MCPClient(self.mcp_server_url) as mcp:
                # First, get the current skill code
                try:
                    # Try to get skill code via MCP (if available) or direct API call
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{self.mcp_server_url.replace('/mcp', '')}/skills/{skill_name}/code")
                        if response.status_code == 200:
                            skill_data = response.json()
                            current_code = skill_data.get("code", "")
                        else:
                            return {
                                "success": False,
                                "error": f"Could not retrieve current code for skill {skill_name}"
                            }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to get current skill code: {str(e)}"
                    }
                
                # Create improvement request
                improvement_request = {
                    "skill_name": skill_name,
                    "current_code": current_code,
                    "improvement_prompt": f"Improve this skill: {improvements}. New description: {new_description}"
                }
                
                # Call the improvement endpoint
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{self.mcp_server_url.replace('/mcp', '')}/skills/improve",
                            json=improvement_request,
                            timeout=60.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("success"):
                                logger.info(f"Successfully improved skill {skill_name}")
                                return {
                                    "success": True,
                                    "improved_skill": result.get("improved_skill"),
                                    "message": f"Successfully improved {skill_name}"
                                }
                            else:
                                return {
                                    "success": False,
                                    "error": result.get("error", "Improvement failed")
                                }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status_code}: {response.text}"
                            }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to call improvement endpoint: {str(e)}"
                    }
                    
        except Exception as e:
            logger.error(f"Error in skill improvement execution: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _attempt_skill_improvement(
        self, 
        skill_name: str, 
        error_message: str,
        failed_parameters: Dict[str, Any]
    ) -> bool:
        """Attempt to automatically improve a failing skill."""
        try:
            # Get current skill code
            response = await self.session.get(f"{self.mcp_server_url}/skills/{skill_name}/code")
            if response.status_code != 200:
                return False
            
            skill_data = response.json()
            current_code = skill_data.get("code", "")
                
            # Generate improvement prompt based on the error
            if "unexpected keyword argument" in error_message:
                # Extract parameter name from error
                import re
                match = re.search(r"unexpected keyword argument '(\w+)'", error_message)
                problem_param = match.group(1) if match else "parameter"
                
                improvement_prompt = f"""Fix parameter mismatch error: The consumer agent is calling this skill with parameter '{problem_param}' but the skill function expects a different parameter name. 
                
Error: {error_message}
Parameters sent: {list(failed_parameters.keys())}

Update the function signature to accept the parameter name '{problem_param}' that the consumer agent is sending. This is a parameter naming issue, not a logic issue."""
            else:
                improvement_prompt = f"""Fix the following error in this skill:

Error: {error_message}
Parameters sent: {failed_parameters}

Please analyze and fix the issue while maintaining the skill's core functionality."""
            
            # Call improvement endpoint
            improvement_request = {
                "skill_name": skill_name,
                "current_code": current_code,
                "improvement_prompt": improvement_prompt
            }
            
            response = await self.session.post(
                f"{self.mcp_server_url}/skills/improve",
                json=improvement_request,
                timeout=60.0
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"Successfully improved skill {skill_name}")
                    return True
                        
            return False
            
        except Exception as e:
            logger.error(f"Failed to improve skill {skill_name}: {e}")
            return False
    
    def _map_parameters_intelligently(
        self, 
        original_params: Dict[str, Any], 
        skill_tool: Dict[str, Any], 
        user_message: str
    ) -> Dict[str, Any]:
        """Map parameters intelligently by understanding common parameter name variations."""
        if not skill_tool or "inputSchema" not in skill_tool:
            return original_params
            
        expected_params = skill_tool["inputSchema"].get("properties", {})
        if not expected_params:
            return original_params
            
        mapped_params = {}
        
        # Common parameter mappings
        parameter_mappings = {
            # Fibonacci sequence variations
            "terms": ["n_terms", "num_terms", "count", "length"],
            "count": ["n_terms", "num_terms", "terms", "length"], 
            "number": ["n_terms", "num_terms", "count", "n"],
            "n": ["n_terms", "num_terms", "number"],
            
            # Number/calculation variations
            "num": ["number", "n", "value"],
            "value": ["number", "n", "num"],
            
            # General variations
            "text": ["string", "str", "input"],
            "string": ["text", "str", "input"],
            "input": ["text", "string", "str"],
        }
        
        for param_name, param_value in original_params.items():
            # First, try exact match
            if param_name in expected_params:
                mapped_params[param_name] = param_value
                continue
                
            # Try to find a mapping
            mapped = False
            if param_name in parameter_mappings:
                for candidate in parameter_mappings[param_name]:
                    if candidate in expected_params:
                        mapped_params[candidate] = param_value
                        logger.info(f"Parameter mapping: {param_name} -> {candidate}")
                        mapped = True
                        break
            
            # If no mapping found, keep original (might still work)
            if not mapped:
                mapped_params[param_name] = param_value
                
        return mapped_params
    
    async def _execute_skill_with_retry(
        self, 
        mcp: MCPClient, 
        skill_name: str, 
        parameters: Dict[str, Any], 
        skill_tool: Dict[str, Any]
    ) -> tuple[Any, Optional[Dict[str, Any]]]:
        """Execute skill with intelligent retry on parameter errors."""
        retry_info = None
        
        try:
            # First attempt
            result = await mcp.call_tool(skill_name, parameters)
            
            # Check if the result contains an error (MCP errors come back as results)
            if isinstance(result, dict) and "error" in result:
                error_str = str(result["error"])
                if "unexpected keyword argument" in error_str:
                    # Handle the error as if it was an exception
                    raise Exception(error_str)
            
            return result, retry_info
            
        except Exception as e:
            error_str = str(e)
            
            # Check for parameter mismatch errors (both in exceptions and MCP error responses)
            if "unexpected keyword argument" in error_str or "got an unexpected keyword argument" in error_str:
                retry_info = {"original_error": error_str, "corrections_attempted": []}
                
                # Extract the problematic parameter from error message
                # Error format: "function() got an unexpected keyword argument 'param_name'"
                import re
                match = re.search(r"unexpected keyword argument '(\w+)'", error_str)
                if match:
                    problem_param = match.group(1)
                    retry_info["problem_parameter"] = problem_param
                    
                    # Try to find the correct parameter name
                    expected_params = skill_tool.get("inputSchema", {}).get("properties", {})
                    
                    # Remove the problematic parameter and try common variations
                    corrected_params = {k: v for k, v in parameters.items() if k != problem_param}
                    problem_value = parameters.get(problem_param)
                    
                    # Common parameter name corrections
                    corrections_to_try = []
                    if problem_param == "terms":
                        corrections_to_try = ["n_terms", "num_terms", "count"]
                    elif problem_param == "count":
                        corrections_to_try = ["n_terms", "terms", "num_terms"]
                    elif problem_param == "number":
                        corrections_to_try = ["n", "num", "value"]
                    
                    # Try each correction
                    for correction in corrections_to_try:
                        if correction in expected_params:
                            corrected_params[correction] = problem_value
                            retry_info["corrections_attempted"].append({
                                "from": problem_param,
                                "to": correction,
                                "value": problem_value
                            })
                            
                            logger.info(f"Retrying {skill_name} with parameter correction: {problem_param} -> {correction}")
                            
                            try:
                                result = await mcp.call_tool(skill_name, corrected_params)
                                
                                # Check if retry result also has an error
                                if isinstance(result, dict) and "error" in result:
                                    logger.warning(f"Retry with {correction} failed: {result['error']}")
                                    continue
                                    
                                retry_info["successful_correction"] = correction
                                return result, retry_info
                            except Exception as retry_e:
                                logger.warning(f"Retry with {correction} failed: {retry_e}")
                                continue
            
            # If no successful retry, try automatic skill improvement
            logger.info(f"Parameter retries failed for {skill_name}, attempting automatic improvement")
            
            try:
                improved = await self._attempt_skill_improvement(skill_name, error_str, parameters)
                if improved:
                    logger.info(f"Successfully improved skill {skill_name}, retrying...")
                    # Retry with original parameters after improvement
                    result = await mcp.call_tool(skill_name, parameters)
                    if not (isinstance(result, dict) and "error" in result):
                        retry_info["automatic_improvement"] = True
                        return result, retry_info
            except Exception as improvement_error:
                logger.warning(f"Automatic improvement failed: {improvement_error}")
            
            # If no successful retry or improvement, return original error as a result (not exception)
            return {"error": error_str}, retry_info
    
    def _is_complex_request(self, user_message: str, available_tools: List[Dict[str, Any]]) -> bool:
        """Determine if a user request is complex enough to warrant skill creation."""
        user_lower = user_message.lower()
        
        # Simple requests that don't need new skills
        simple_patterns = [
            "hello", "hi", "hey", "thanks", "thank you", "what can you help",
            "what can you do", "list skills", "show capabilities", "help",
            "how are you", "who are you", "what are you"
        ]
        
        if any(pattern in user_lower for pattern in simple_patterns):
            return False
            
        # Requests that are already covered by existing tools
        covered_patterns = []
        for tool in available_tools:
            tool_name = tool.get("name", "").lower()
            tool_desc = tool.get("description", "").lower()
            
            # Add patterns based on existing tool capabilities
            if "add" in tool_name or "addition" in tool_desc:
                covered_patterns.extend(["add", "plus", "sum"])
            if "multiply" in tool_name or "multiplication" in tool_desc:
                covered_patterns.extend(["multiply", "times", "product"])
            if "calculator" in tool_name:
                covered_patterns.extend(["calculate", "compute"])
            if "count" in tool_name:
                covered_patterns.extend(["count", "how many"])
                
        if any(pattern in user_lower for pattern in covered_patterns):
            return False
            
        # Consider it complex if it's not a simple greeting/question and not covered
        return len(user_message.strip()) > 10
    
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
    
    def _extract_result_value(self, mcp_result: Any) -> Any:
        """Extract the actual value from MCP result format."""
        try:
            # Handle the nested structure: {'content': [{'type': 'text', 'text': "{'result': 8.0}"}], 'isError': False}
            if isinstance(mcp_result, dict):
                if 'content' in mcp_result and isinstance(mcp_result['content'], list):
                    for content_item in mcp_result['content']:
                        if isinstance(content_item, dict) and content_item.get('type') == 'text':
                            text = content_item.get('text', '')
                            if text:
                                # Try to parse as JSON/dict
                                try:
                                    import ast
                                    parsed = ast.literal_eval(text)
                                    if isinstance(parsed, dict) and 'result' in parsed:
                                        return parsed['result']
                                except:
                                    pass
                                # Fallback: return the text
                                return text
                # If no content found, check if there's a direct result
                if 'result' in mcp_result:
                    return mcp_result['result']
            
            # Fallback: return the original result
            return mcp_result
        except Exception as e:
            logger.warning(f"Failed to extract result value: {e}")
            return mcp_result
    
    async def _get_skill_suggestions(
        self, 
        user_message: str, 
        available_tools: List[Dict[str, Any]]
    ) -> List[SkillSuggestion]:
        """Get skill suggestions based on user message and available tools."""
        
        suggestions = []
        user_lower = user_message.lower()
        
        # Don't suggest skills for basic math that we can already handle
        basic_math_keywords = ["add", "plus", "+", "sum", "multiply", "times", "*", "subtract", "minus", "divide"]
        if any(keyword in user_lower for keyword in basic_math_keywords):
            # For basic math, we don't need suggestions since we handle it automatically
            return []
        
        for tool in available_tools:
            name = tool.get("name", "")
            description = tool.get("description", "")
            
            # More sophisticated relevance scoring
            relevance = 0.0
            words = user_lower.split()
            
            # Higher score for exact name matches in user message
            if name.lower() in user_lower:
                relevance += 0.8
                
            # Score for individual word matches
            for word in words:
                if len(word) > 3:  # Only consider meaningful words
                    if word in name.lower():
                        relevance += 0.4
                    if word in description.lower():
                        relevance += 0.3
            
            # Special scoring for specific skill types that might be genuinely useful
            if "help" in user_lower or "what can you do" in user_lower:
                if "list" in name.lower():
                    relevance += 0.5
                    
            # Only suggest if highly relevant (raised threshold)
            if relevance >= 0.6:
                suggestions.append(SkillSuggestion(
                    skill_name=name,
                    description=description,
                    relevance_score=min(relevance, 1.0),
                    reason=self._get_suggestion_reason(name, description, user_message)
                ))
                
        # Sort by relevance and return top 2 (reduced from 3)
        suggestions.sort(key=lambda x: x.relevance_score, reverse=True)
        return suggestions[:2]
    
    def _get_suggestion_reason(self, skill_name: str, description: str, user_message: str) -> str:
        """Generate a specific reason for why this skill is suggested."""
        user_lower = user_message.lower()
        
        if skill_name.lower() in user_lower:
            return f"You mentioned '{skill_name}' directly"
        
        if "help" in user_lower or "what can you do" in user_lower:
            return "This skill can help you explore available capabilities"
            
        return "This skill seems relevant to your request"
        
    async def request_skill_generation(
        self, 
        session_id: str, 
        skill_description: str,
        skill_name: Optional[str] = None,
        available_skills: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Request generation of a new skill from AutoLearn server."""
        
        try:
            # Use the REST API directly for skill generation
            from .openai_client import get_openai_client
            from .schemas import GenerateSkillRequest
            
            # Enhance the description with available skills context
            enhanced_description = skill_description
            if available_skills:
                skills_context = "\n\nAvailable skills that can be called from this new skill:\n"
                for skill in available_skills:
                    skills_context += f"- {skill['name']}: {skill.get('description', 'No description')}\n"
                    if 'inputSchema' in skill and 'properties' in skill['inputSchema']:
                        params = skill['inputSchema']['properties']
                        if params:
                            param_info = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in params.items())
                            skills_context += f"  Parameters: {param_info}\n"
                
                enhanced_description += skills_context
                enhanced_description += "\nNote: This skill should use existing skills when appropriate by calling them with proper parameters."
            
            # Get the configured OpenAI client and generation request
            openai_client = get_openai_client()
            generation_req = GenerateSkillRequest(
                description=enhanced_description,
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
        # First check if we have it in memory
        if session_id in self.conversations:
            return self.conversations[session_id]
        
        # If not in memory, try to load from database
        try:
            db_session = db.get_session(session_id)
            if db_session and db_session.messages:
                # Convert database messages to conversation context
                messages = []
                for msg in db_session.messages:
                    messages.append(ConversationMessage(
                        role=msg.role,
                        content=msg.content,
                        timestamp=msg.timestamp,
                        metadata={}
                    ))
                
                context = ConversationContext(
                    session_id=session_id,
                    messages=messages,
                    skills_used=[],  # TODO: Extract from message metadata
                    skills_requested=[]  # TODO: Extract from message metadata
                )
                
                # Cache in memory for future use
                self.conversations[session_id] = context
                return context
        except Exception as e:
            logger.error(f"Error loading session from database: {e}")
        
        return None


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
