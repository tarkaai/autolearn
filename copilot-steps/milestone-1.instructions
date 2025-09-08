Title: Milestone 1 - Backend scaffold (FastAPI) and SkillEngine stub

Summary:
- Implement a minimal, production-friendly backend scaffold for AutoLearn.
- Deliver a FastAPI app exposing MCP-like endpoints, a health check, and a lightweight SkillEngine stub with an in-memory registry and one hardcoded skill.

Top-level goals (from PRD):
- FastAPI server with MCP endpoints and health check.
- SkillEngine stub with hardcoded skills.
- Python 3.11+ compatible, clear typing, and tests for the scaffold.

What Copilot should produce (concrete):
1. A package layout under a new `backend/` folder with minimal files:
   - `backend/app.py` (FastAPI app, startup/shutdown hooks, health endpoint)
   - `backend/mcp.py` (MCP endpoints: `/tools`, `/run`, and `/mcp` or `/spec` to fetch current MCP schema)
   - `backend/skill_engine.py` (SkillEngine class: register, list, execute; in-memory registry; one hardcoded skill `echo` or `sum_numbers`)
   - `backend/schemas.py` (pydantic models for skill metadata, run requests, responses)
   - `backend/__init__.py`
   - `tests/test_backend_basic.py` (pytests: app starts, health check returns 200, registering/listing skills works)
   - `pyproject.toml` or `requirements.txt` (minimal dependencies: fastapi, uvicorn, pydantic, pytest)

Style & constraints (must follow):
- Use Python 3.11 syntax and typing (TypedDict/Annotated where helpful).
- Keep code small and explicit; prefer clarity over clever metaprogramming.
- No external network calls in the scaffold (OpenAI integration is out-of-scope for Milestone 1).
- Use dependency injection (FastAPI's Depends) where appropriate for the SkillEngine instance.
- Include docstrings for public functions/classes and small inline comments explaining intent.
- Avoid persisting to disk; registry should be in-memory for now but include a clear TODO to add JSON persistence.

APIs (surface contract):
- GET /health -> 200, {"status":"ok"}
- GET /tools -> list registered skills (their metadata form matching `schemas.SkillMeta`)
- POST /run -> run a registered skill by name with args -> returns structured result or error
- GET /mcp -> returns a JSON object representing the current MCP spec (derived from skill metadata)

SkillEngine contract (2-3 bullets):
- register(skill_meta: SkillMeta, func: Callable) -> None
- list_skills() -> list[SkillMeta]
- run(name: str, args: dict) -> dict | raises SkillNotFound/SkillRuntimeError

Acceptance criteria (tests to produce):
- Tests start the FastAPI TestClient and assert `/health` returns 200 with expected body.
- Register a hardcoded skill (`echo` or `sum_numbers`) on startup; `/tools` lists it.
- POST to `/run` for the hardcoded skill returns the correct result for a simple payload.

Edge cases & notes for Copilot:
- Validate input types via Pydantic schemas; return 400 on malformed requests.
- `/run` should catch exceptions from skill execution and return a 500-style JSON error with message and traceback truncated.
- Log (print or logging) important lifecycle events (startup, shutdown, skill registered, skill executed).
- Keep all secret or risky behavior out of this milestone (no eval of untrusted code, no shell calls).

Files and small templates Copilot may generate (examples):
- backend/skill_engine.py
  - class SkillEngine:
    - __init__(self): self._registry: dict[str, tuple[SkillMeta, Callable]] = {}
    - register(self, meta, func): ...
    - list_skills(self): ...
    - run(self, name, args): ...

- backend/app.py
  - from fastapi import FastAPI, Depends
  - from .skill_engine import SkillEngine
  - app = FastAPI()
  - @app.on_event('startup') register hardcoded skill

Security & safety checklist for milestone 1:
- Do not execute arbitrary code from user input.
- Return safe, structured error messages (no raw tracebacks) in API responses.
- Mark places that will later call OpenAI with TODO comments and guardrails.

What to hand off to next milestone (explicit TODOs):
- Replace SkillEngine stub with OpenAI generation pipeline.
- Add JSON or DB persistence and migration for skills.
- Add sandboxing or restricted execution environment.

Developer guidance for running locally (short):
- Use `uvicorn backend.app:app --reload` to run the server.
- Use `pytest` to run tests.

Notes and assumptions (brief):
- This milestone focuses on internal API and developer DX; the frontend and OpenAI pieces come later.
- Use minimal dependencies to keep CI fast and predictable.
