"""FastAPI app for AutoLearn Milestone 1."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .schemas import RunRequest, RunResponse, SkillMeta
from .skill_engine import SkillEngine, SkillNotFound, SkillRuntimeError, create_default_engine

logger = logging.getLogger("autolearn")


def get_engine() -> SkillEngine:
    # In a real app this would be wired from app.state or DI container
    return create_default_engine()


app = FastAPI(title="AutoLearn Milestone 1")


@app.on_event("startup")
def _on_startup() -> None:
    logger.info("Starting AutoLearn Milestone 1 app")


@app.on_event("shutdown")
def _on_shutdown() -> None:
    logger.info("Shutting down AutoLearn Milestone 1 app")


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
