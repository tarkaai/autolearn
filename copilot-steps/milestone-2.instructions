Title: Milestone 2 – OpenAI Integration and Dynamic Skill Generation

Summary:
- Extend the backend to support dynamic skill creation from natural language using OpenAI models.
- Implement endpoints and logic for generating, registering, and executing new skills at runtime.
- Keep the MCP spec in sync with new skills.

Top-level goals (from PRD):
- Integrate OpenAI (gpt-4.1, gpt-4.1-mini) for code generation.
- Allow agents/users to define new skills via natural language.
- Register and execute new skills dynamically.
- Update MCP spec in real time as new skills are added.

What Copilot should produce (concrete):
1. Extend backend/SkillEngine to support dynamic registration of skills from generated code.
2. Add OpenAI integration module (backend/openai_client.py) with safe, testable API for code generation.
3. Add endpoint (e.g., POST /skills/generate) to accept NL requests and return generated skill metadata/code.
4. Add endpoint (e.g., POST /skills/register) to register a new skill from generated code.
5. Update MCP endpoints to reflect new skills immediately.
6. Add/extend tests to cover skill generation, registration, and execution.
7. Add error handling, logging, and TODOs for sandboxing and security review.

Style & constraints (must follow):
- Use Python 3.11+ typing and Pydantic models.
- No raw eval/exec of untrusted code; use safe code compilation and clear TODOs for sandboxing.
- All OpenAI API keys/config must be loaded from environment variables (never hardcoded).
- Add clear docstrings and inline comments for all new logic.
- No frontend or persistence changes in this milestone (unless required for demo/testing).

APIs (surface contract):
- POST /skills/generate {"description": str, ...} -> {"code": str, "meta": SkillMeta, ...}
- POST /skills/register {"code": str, "meta": SkillMeta, ...} -> {"success": bool, ...}
- Existing endpoints (/tools, /run, /mcp) must reflect new skills after registration.

Acceptance criteria (tests to produce):
- Test OpenAI integration (mocked) returns valid Python code for a skill.
- Test registering a generated skill adds it to the registry and MCP spec.
- Test executing a newly registered skill via /run returns correct result.
- Test error handling for invalid code, registration, and execution.

Edge cases & notes for Copilot:
- Validate all generated code before registration; reject/raise on unsafe or invalid code.
- Log all skill generation and registration events.
- Mark all places where sandboxing or code safety review is needed with TODOs.
- Do not persist skills to disk yet (in-memory only).

What to hand off to next milestone (explicit TODOs):
- Add persistent storage for skills (JSON/DB).
- Add frontend UI for skill creation and inspection.
- Add sandboxed/restricted execution environment for skills.

Developer guidance for running locally (short):
- Set OPENAI_API_KEY in your environment.
- Use `uvicorn backend.app:app --reload` to run the server.
- Use `pytest` to run tests (mock OpenAI for CI).

Notes and assumptions:
- This milestone focuses on backend dynamic skill generation and registration only.
- Frontend and persistence come in later milestones.
