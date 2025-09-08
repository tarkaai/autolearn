"""FastAPI app for AutoLearn Milestone 3."""

from __future__ import annotations

import os
import json
import logging
from typing import Optional, Any, List
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    GenerateSkillRequest, 
    GenerateSkillResponse, 
    RegisterSkillRequest, 
    RegisterSkillResponse,
    GetSkillCodeResponse,
    RunRequest, 
    RunResponse, 
    SkillMeta,
    ChatSession,
    ChatMessage,
    CreateSessionRequest,
    CreateSessionResponse,
    AddMessageRequest,
    AddMessageResponse
)
from .skill_engine import (
    SkillEngine, 
    SkillNotFound, 
    SkillRuntimeError, 
    SkillRegistrationError,
    create_default_engine,
    get_mcp_spec,
    get_engine
)
from .openai_client import OpenAIClient, SkillGenerationRequest, create_default_client, get_openai_client
from . import websocket
from . import sessions
from . import db
from .mcp_protocol import MCPProtocolHandler

logger = logging.getLogger("autolearn")

# Create the FastAPI app
app = FastAPI(title="AutoLearn Milestone 3")

# Add CORS middleware to allow cross-origin requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





@app.on_event("startup")
async def _on_startup() -> None:
    """Initialize the app with a shared SkillEngine instance and WebSocket."""
    logger.info("Starting AutoLearn Milestone 3 app")
    
    # Initialize database
    db.init_db()
    
    # Initialize the global SkillEngine instance
    engine = get_engine()
    
    # Initialize MCP protocol handler
    app.state.mcp_handler = MCPProtocolHandler(engine)
    logger.info("MCP protocol handler initialized")
    
    # Set up WebSocket (keep for demo frontend)
    await websocket.setup_socketio(app)
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY environment variable not set. "
            "OpenAI integration will not work until this is configured."
        )


@app.on_event("shutdown")
def _on_shutdown() -> None:
    logger.info("Shutting down AutoLearn Milestone 3 app")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/tools")
def tools(engine: SkillEngine = Depends(get_engine)) -> list[SkillMeta]:
    """Return a list of all registered skills."""
    return engine.list_skills()


# Session management endpoints

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
    message = sessions.add_message(session_id, request)
    if not message:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    # If this is a user message, generate an assistant response
    # This is a DEMO of how an MCP client might interact with our server
    generated_skill = None
    if request.role == "user":
        # Simple demo responses showing MCP server capabilities
        user_content = request.content.lower()
        
        if "hello" in user_content or "hi " in user_content:
            assistant_content = "Hello! I'm AutoLearn, an MCP server. I can help you create and execute skills. Try asking me to 'list skills' or 'create a skill that adds numbers'."
        elif "list skills" in user_content or "what skills" in user_content:
            skills = engine.list_skills()
            if skills:
                skill_list = "\n".join([f"- {skill.name}: {skill.description}" for skill in skills])
                assistant_content = f"Available skills:\n{skill_list}\n\nYou can execute these via the MCP /run endpoint or ask me to create new ones."
            else:
                assistant_content = "No skills available yet. Try asking me to create one!"
        elif "create a skill" in user_content:
            try:
                # Extract skill description
                description = user_content.split("create a skill", 1)[1].strip()
                if description.startswith("that "):
                    description = description[5:]
                
                if description:
                    # Generate a skill using OpenAI
                    generation_req = SkillGenerationRequest(
                        description=description,
                        name=None
                    )
                    result = openai_client.generate_skill_code(generation_req)
                    
                    # Register the skill
                    engine.register_from_code(result.code, result.meta)
                    generated_skill = result.meta.name
                    
                    # Emit WebSocket events
                    await websocket.emit_skill_added(result.meta.dict())
                    mcp_spec = get_mcp_spec(engine)
                    await websocket.emit_mcp_updated(mcp_spec)
                    
                    assistant_content = f"✅ Created skill '{result.meta.name}'! This skill can now be called via MCP. Description: {result.meta.description}"
                else:
                    assistant_content = "Please provide a description of what skill you'd like me to create."
            except Exception as e:
                logger.exception(f"Error generating skill: {e}")
                assistant_content = f"Sorry, I couldn't create that skill. Error: {str(e)}"
        elif any(skill.name in user_content for skill in engine.list_skills()):
            # User mentioned a skill name - suggest how to use it
            mentioned_skills = [skill.name for skill in engine.list_skills() if skill.name in user_content]
            if mentioned_skills:
                skill_name = mentioned_skills[0]
                assistant_content = f"I see you mentioned '{skill_name}'. You can execute this skill via the MCP server using the /run endpoint, or through the Execute panel in the frontend."
            else:
                assistant_content = "I understand you want to use a skill, but I'm not sure which one. Type 'list skills' to see available skills."
        else:
            assistant_content = "I'm AutoLearn, an MCP server for dynamic skill creation. I can:\n• List available skills\n• Create new skills from descriptions\n• Execute skills via MCP protocol\n\nTry: 'list skills' or 'create a skill that multiplies numbers'"
        
        # Add assistant response to session
        assistant_req = AddMessageRequest(
            role="assistant", 
            content=assistant_content
        )
        assistant_msg = sessions.add_message(session_id, assistant_req)
        
        # For demonstration purposes, check if the message contains "create a skill"
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


@app.post("/run")
async def run(req: RunRequest, engine: SkillEngine = Depends(get_engine)) -> RunResponse:
    try:
        result = engine.run(req.name, req.args)
        response = RunResponse(success=True, result=result)
        
        # Emit WebSocket event for skill execution
        execution_result = {
            "skill": req.name,
            "args": req.args,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        await websocket.emit_skill_executed(execution_result)
        
        return response
    except SkillNotFound:
        raise HTTPException(status_code=404, detail=f"Skill not found: {req.name}")
    except SkillRuntimeError as e:
        # Avoid leaking full traceback to clients; include a short message
        logger.exception("Skill runtime error")
        return RunResponse(success=False, error=str(e))



@app.get("/mcp")
async def mcp(engine: SkillEngine = Depends(get_engine)) -> dict:
    """Return a full MCP-style spec generated from registered skills."""
    return get_mcp_spec(engine)


@app.post("/mcp")
async def mcp_jsonrpc(request: Request) -> JSONResponse:
    """
    MCP JSON-RPC over HTTP endpoint.
    
    This endpoint handles MCP protocol messages over HTTP transport.
    MCP clients can connect to this endpoint to use AutoLearn skills.
    """
    try:
        # Ensure MCP handler is initialized (fallback for tests)
        if not hasattr(request.app.state, 'mcp_handler'):
            engine = get_engine()
            request.app.state.mcp_handler = MCPProtocolHandler(engine)
            logger.info("MCP protocol handler initialized (fallback)")
        
        # Get the JSON-RPC message from request body
        message = await request.body()
        message_str = message.decode('utf-8')
        
        # Handle the message through MCP protocol handler
        response = await request.app.state.mcp_handler.handle_message(message_str)
        
        # Return the response
        if response:
            # Parse the JSON string back to dict for JSONResponse
            import json
            response_dict = json.loads(response)
            return JSONResponse(content=response_dict)
        else:
            # No response for notifications
            return JSONResponse(content={}, status_code=204)
            
    except Exception as e:
        logger.error(f"MCP endpoint error: {str(e)}")
        return JSONResponse(
            content={
                "jsonrpc": "2.0", 
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": None
            },
            status_code=500
        )


@app.post("/skills/generate")
async def generate_skill(
    req: GenerateSkillRequest,
    openai_client: OpenAIClient = Depends(get_openai_client)
) -> GenerateSkillResponse:
    """Generate Python code for a new skill based on natural language description."""
    try:
        # Convert our API schema to OpenAI client schema
        generation_req = SkillGenerationRequest(
            description=req.description,
            name=req.name,
            inputs=req.inputs
        )
        
        # Call OpenAI to generate the code
        result = openai_client.generate_skill_code(generation_req)
        
        # Convert the result to our API schema
        meta_dict = result.meta
        if not isinstance(meta_dict, dict):
            raise ValueError("Generated metadata is not a dictionary")
            
        # Create a proper SkillMeta object from the dict
        meta = SkillMeta(
            name=meta_dict.get("name", req.name or "unnamed_skill"),
            description=meta_dict.get("description", req.description),
            version=meta_dict.get("version", "0.1.0"),
            inputs=meta_dict.get("inputs", {})
        )
        
        return GenerateSkillResponse(
            success=True,
            code=result.code,
            meta=meta
        )
    
    except Exception as e:
        logger.exception("Error generating skill")
        return GenerateSkillResponse(
            success=False,
            error=f"Failed to generate skill: {str(e)}"
        )


@app.post("/skills/register")
async def register_skill(
    req: RegisterSkillRequest,
    engine: SkillEngine = Depends(get_engine)
) -> RegisterSkillResponse:
    """Register a new skill from generated code."""
    try:
        # Register the skill from code
        engine.register_from_code(req.code, req.meta)
        
        # Emit WebSocket events for skill registration
        await websocket.emit_skill_added(req.meta.dict())
        
        # Update MCP spec and emit event
        mcp_spec = get_mcp_spec(engine)
        await websocket.emit_mcp_updated(mcp_spec)
        
        return RegisterSkillResponse(
            success=True,
            name=req.meta.name
        )
    
    except SkillRegistrationError as e:
        logger.exception("Error registering skill")
        return RegisterSkillResponse(
            success=False,
            error=f"Failed to register skill: {str(e)}"
        )


@app.get("/skills/{name}/code")
async def get_skill_code(
    name: str,
    engine: SkillEngine = Depends(get_engine)
) -> GetSkillCodeResponse:
    """Get the source code for a registered skill."""
    try:
        code = engine.get_skill_code(name)
        return GetSkillCodeResponse(
            name=name,
            code=code
        )
    except SkillNotFound:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    except Exception as e:
        logger.exception(f"Error retrieving skill code for {name}")
        raise HTTPException(status_code=500, detail=f"Error retrieving skill code: {str(e)}")


@app.delete("/skills/{name}")
async def delete_skill(
    name: str,
    engine: SkillEngine = Depends(get_engine)
) -> dict:
    """Delete a registered skill."""
    try:
        engine.unregister(name)
        return {"success": True, "message": f"Skill '{name}' unregistered successfully"}
    except SkillNotFound:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    except Exception as e:
        logger.exception(f"Error unregistering skill: {name}")
        raise HTTPException(status_code=500, detail=f"Error unregistering skill: {str(e)}")
