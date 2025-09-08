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
    generated_skill = None
    if request.role == "user":
        # For now, we'll just echo the message as the assistant
        # In a real implementation, this would call OpenAI and potentially generate skills
        assistant_req = AddMessageRequest(
            role="assistant",
            content=f"I received your message: {request.content}"
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
