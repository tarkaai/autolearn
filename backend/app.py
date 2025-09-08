"""FastAPI app for AutoLearn Milestone 1."""

from __future__ import annotations

import logging
import os
from typing import Optional, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .schemas import (
    GenerateSkillRequest, 
    GenerateSkillResponse, 
    RegisterSkillRequest, 
    RegisterSkillResponse,
    GetSkillCodeResponse,
    RunRequest, 
    RunResponse, 
    SkillMeta
)
from .skill_engine import (
    SkillEngine, 
    SkillNotFound, 
    SkillRuntimeError, 
    SkillRegistrationError,
    create_default_engine
)
from .openai_client import OpenAIClient, SkillGenerationRequest, create_default_client

logger = logging.getLogger("autolearn")


def get_engine() -> SkillEngine:
    """Dependency for getting the SkillEngine instance.
    
    In Milestone 1, this created a new engine each time. For Milestone 2,
    we'll store a shared instance in app.state for persistence across requests.
    """
    return app.state.engine


def get_openai_client() -> OpenAIClient:
    """Dependency for getting the OpenAI client instance."""
    if not hasattr(app.state, "openai_client"):
        app.state.openai_client = create_default_client()
    return app.state.openai_client


app = FastAPI(title="AutoLearn Milestone 2")


@app.on_event("startup")
def _on_startup() -> None:
    """Initialize the app with a shared SkillEngine instance."""
    logger.info("Starting AutoLearn Milestone 2 app")
    
    # Create and store a single SkillEngine instance for the app
    app.state.engine = create_default_engine()
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY environment variable not set. "
            "OpenAI integration will not work until this is configured."
        )


@app.on_event("shutdown")
def _on_shutdown() -> None:
    logger.info("Shutting down AutoLearn Milestone 2 app")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/tools")
def list_tools(engine: SkillEngine = Depends(get_engine)) -> list[SkillMeta]:
    return engine.list_skills()


@app.post("/run")
def run(req: RunRequest, engine: SkillEngine = Depends(get_engine)) -> RunResponse:
    try:
        result = engine.run(req.name, req.args)
        return RunResponse(success=True, result=result)
    except SkillNotFound:
        raise HTTPException(status_code=404, detail=f"Skill not found: {req.name}")
    except SkillRuntimeError as e:
        # Avoid leaking full traceback to clients; include a short message
        logger.exception("Skill runtime error")
        return RunResponse(success=False, error=str(e))


@app.get("/mcp")
def mcp(engine: SkillEngine = Depends(get_engine)) -> dict:
    """Return a minimal MCP-style spec generated from registered skills."""
    tools = []
    for meta in engine.list_skills():
        tools.append({
            "name": meta.name,
            "description": meta.description,
            "version": meta.version,
            "inputs": meta.inputs,
        })
    return {"mcp_version": "0.1", "tools": tools}


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
