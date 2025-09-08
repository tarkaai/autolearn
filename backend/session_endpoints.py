# Session management endpoints

import json
import logging
from typing import List, Optional

from fastapi import Depends, HTTPException

from . import sessions, websocket
from .openai_client import OpenAIClient, get_openai_client
from .schemas import (
    AddMessageRequest, 
    AddMessageResponse, 
    ChatMessage, 
    ChatSession,
    CreateSessionRequest, 
    CreateSessionResponse,
    SkillGenerationRequest,
    SkillMeta
)
from .skill_engine import SkillEngine, get_mcp_spec, get_engine

from .app import app

logger = logging.getLogger("autolearn.session_endpoints")

@app.post("/sessions")
async def create_session(
    request: CreateSessionRequest
) -> CreateSessionResponse:
    """Create a new chat session."""
    session = sessions.create_session(request)
    return CreateSessionResponse(session=session)


@app.get("/sessions")
async def list_sessions() -> List[ChatSession]:
    """List all chat sessions."""
    return sessions.list_sessions()


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> ChatSession:
    """Get a chat session by ID."""
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return session


@app.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str,
    request: AddMessageRequest,
    openai_client: OpenAIClient = Depends(get_openai_client),
    engine: SkillEngine = Depends(get_engine)
) -> AddMessageResponse:
    """Add a message to a chat session."""
    logger.info(f"add_message called: session={session_id}, role={request.role}")
    logger.info(f"OpenAI client: {openai_client is not None}, Engine: {engine is not None}")
    
    message = sessions.add_message(session_id, request)
    if not message:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    # If this is a user message, generate an assistant response
    generated_skill = None
    if request.role == "user":
        logger.info(f"Processing user message: {request.content[:50]}...")
        # Get the conversation history
        session = sessions.get_session(session_id)
        chat_history = session.messages if session else []
        
        # Get available tools from MCP spec
        mcp_spec = get_mcp_spec(engine)
        available_tools = mcp_spec.get("tools", [])
        
        # Prepare the conversation for OpenAI
        system_prompt = f"""You are AutoLearn, an AI assistant powered by a Model Context Protocol (MCP) server that provides dynamic skill creation and execution capabilities.

AUTOLEARN MCP SERVER SPECIFICATION:
- Server Name: AutoLearn
- Version: 0.1.0  
- Purpose: Dynamic skill creation for AI agents
- Available Tools: {len(available_tools)} skills/functions

AVAILABLE SKILLS: {', '.join([tool['function']['name'] + ': ' + tool['function']['description'] for tool in available_tools])}

CORE CAPABILITIES:
1. **Skill Execution**: Use existing skills via function calls to accomplish user tasks
2. **Skill Creation**: Generate new Python skills when users request functionality not yet available
3. **Skill Management**: List, describe, and combine multiple skills for complex workflows

BEHAVIOR GUIDELINES:
- ALWAYS use available function calls when users request skill usage or task execution
- When asked "what skills do you have", call functions to demonstrate capabilities  
- When asked to "use the [skill_name] skill", immediately call that function
- For skill creation requests, explain the skill being created and how it will work
- Be proactive in suggesting and using relevant skills for user goals

MCP PROTOCOL: You operate through function calling as defined by the Model Context Protocol specification. Each skill is exposed as a function tool that you can invoke to provide real functionality to users.

Remember: You are not just a conversational AI - you are a skill execution engine! Use your functions!"""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add previous messages (limit to last 10 for context window)
        for msg in chat_history[-10:]:
            if msg.role in ["user", "assistant", "system"]:
                messages.append({"role": msg.role, "content": msg.content})
        
        try:
            # Prepare function calling parameters
            call_params = {
                "model": openai_client.config.model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # Add tools if available
            if available_tools:
                call_params["tools"] = available_tools
                call_params["tool_choice"] = "auto"
                logger.info(f"Calling OpenAI with {len(available_tools)} tools available")
                logger.debug(f"Available tools: {[t['function']['name'] for t in available_tools]}")
                logger.debug(f"System prompt: {system_prompt[:200]}...")
            else:
                logger.warning("No tools available for OpenAI function calling")
            
            # Call OpenAI to generate a response
            logger.info(f"Making OpenAI API call with model: {call_params['model']}")
            response = openai_client.client.chat.completions.create(**call_params)
            
            # Handle the response
            assistant_content = ""
            tool_calls = response.choices[0].message.tool_calls
            logger.info(f"OpenAI response received. Tool calls: {len(tool_calls) if tool_calls else 0}")
            
            if tool_calls:
                # Handle tool calls
                messages.append(response.choices[0].message)
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    try:
                        # Execute the skill
                        result = engine.run_skill(function_name, **function_args)
                        
                        # Add tool response to messages
                        tool_response = {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(result)
                        }
                        messages.append(tool_response)
                        
                        # Emit WebSocket event for skill execution
                        await websocket.emit_skill_executed({
                            "skill_name": function_name,
                            "inputs": function_args,
                            "result": result
                        })
                        
                    except Exception as e:
                        logger.exception(f"Error executing skill {function_name}")
                        # Add error response
                        tool_response = {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": f"Error executing skill: {str(e)}"
                        }
                        messages.append(tool_response)
                
                # Get final response from OpenAI after tool execution
                final_response = openai_client.client.chat.completions.create(
                    model=openai_client.config.model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                assistant_content = final_response.choices[0].message.content
            else:
                # No tool calls, use the direct response
                assistant_content = response.choices[0].message.content
                logger.info(f"No tool calls, using direct response: {assistant_content[:100]}...")
            
            # Add the assistant message to the session
            assistant_req = AddMessageRequest(
                role="assistant", 
                content=assistant_content
            )
            assistant_msg = sessions.add_message(session_id, assistant_req)
            logger.info(f"Added assistant message to session")
            
            # Return the assistant message instead of the user message
            message = assistant_msg
            
        except Exception as e:
            logger.exception("Error generating assistant response")
            assistant_req = AddMessageRequest(
                role="assistant",
                content=f"I'm sorry, I encountered an error: {str(e)}"
            )
            assistant_msg = sessions.add_message(session_id, assistant_req)
            # Return the assistant message
            message = assistant_msg
            
            # Check if the message contains "create a skill"
        if "create a skill" in request.content.lower():
            # Extract a skill description
            description = request.content.lower().split("create a skill", 1)[1].strip()
            if description:
                try:
                    # Generate a skill
                    generation_req = SkillGenerationRequest(
                        description=description,
                        name=None
                    )
                    result = openai_client.generate_skill_code(generation_req)
                    
                    # Register the skill
                    meta = SkillMeta(**result.meta)
                    engine.register_from_code(result.code, meta)
                    
                    # Update the assistant message to mention the skill
                    assistant_req = AddMessageRequest(
                        role="assistant",
                        content=f"I've created a new skill called '{meta.name}' based on your request. You can now use it!"
                    )
                    assistant_msg = sessions.add_message(session_id, assistant_req)
                    
                    # Save the skill name in the message
                    message.skill_generated = meta.name
                    
                    # Include the skill metadata in the response
                    generated_skill = meta
                    
                    # Emit WebSocket events
                    await websocket.emit_skill_added(meta.dict())
                    mcp_spec = get_mcp_spec(engine)
                    await websocket.emit_mcp_updated(mcp_spec)
                    
                except Exception as e:
                    logger.exception("Error generating skill from chat")
                    assistant_req = AddMessageRequest(
                        role="assistant",
                        content=f"I tried to create a skill but encountered an error: {str(e)}"
                    )
                    assistant_msg = sessions.add_message(session_id, assistant_req)
    
    return AddMessageResponse(message=message, skill_generated=generated_skill)
