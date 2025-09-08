# AutoLearn Product Requirements Document (PRD)

**Product Name:** AutoLearn  
**Owner:** Dan
**Version:** v0.1  

---

## 1. Overview

AutoLearn is a **Model Context Protocol (MCP) server** that extends AI agents with dynamic skill creation. Unlike static MCP servers, AutoLearn introduces a **coding agent** that allows consuming agents to define new **skills** (functional code workflows) from natural language.  

- **Skills as crystalized memory**: workflows preserved as performant, predictable Python code.  
- **Automatic crystalization**: AutoLearn decides what reasoning traces to convert into reusable skills.  
- **Dynamic MCP updates**: new skills appear in the MCP schema in real time.  

AutoLearn is implemented in **Python** with **OpenAI models** for reasoning and code generation. A demo frontend app allows users to chat with a consuming agent, view generated code, inspect the evolving MCP spec, and run new skills.  

---

## 2. Goals

1. Enable consuming agents to create, refine, and reuse skills through natural language.  
2. Automatically crystalize workflows into callable Python functions.  
3. Keep the MCP spec in sync with newly generated skills.  
4. Provide a frontend demo showcasing dynamic skill creation and execution.  

---

## 3. Functional Requirements

### Core MCP Server
- Accepts natural language requests to define skills.  
- Uses OpenAI models (`gpt-4.1`, `gpt-4.1-mini`) to generate/refine Python code.  
- Crystalizes skills based on usage or explicit agent requests.  
- Updates MCP spec dynamically with new skills.  

### Frontend Demo
- **Chat Interface**: user converses with a consuming agent that requests skills.  
- **Skill Viewer**: displays generated Python code.  
- **MCP Viewer**: shows current MCP spec JSON.  
- **Execution Panel**: allows interactive execution of skills.  

### Developer Experience
- Python 3.11+ backend with FastAPI.  
- React + Tailwind frontend.  
- GitHub Copilot should scaffold most implementation with minimal boilerplate.  

---

## 4. Technical Architecture

- **Backend**  
  - FastAPI server.  
  - MCP protocol endpoints (`/tools`, `/run`, updates).  
  - SkillEngine for NL → Python code generation, compilation, and registration.  
  - Registry stored in SQLite database for persistent storage between server restarts.  

- **Frontend**  
  - React app with chat, code viewer, MCP viewer, and execution panel.  
  - WebSocket/HTTP connection to backend for real-time updates.  

- **OpenAI Integration**  
  - `gpt-4.1` for reasoning, `gpt-4.1-mini` for scaffolding.  
  - Function-calling or structured outputs for consistent skill definitions.  

---

## 5. Testing & Validation

### Unit Tests
- Skill generation pipeline produces valid Python code.  
- MCP schema reflects new skills.  
- Skills reload from persistence correctly.  

### Integration Tests
- End-to-end: consuming agent requests → AutoLearn generates skill → skill callable via MCP.  
- Frontend smoke tests: UI renders, connects, and displays updates.  

### Demo Validation
- User sees new skill code and MCP updates in frontend.  
- Skill runs successfully when executed from demo UI.  

---

## 6. Success Metrics

- Agents dynamically create and use skills without manual scripting.  
- MCP spec reflects new skills in real time.  
- Demo app clearly illustrates AutoLearn’s functionality.  

---

## 7. Open Questions

1. Should persistence be limited to SQLite, or should we support additional database options?  
2. What level of sandboxing is required for safe code execution?  
3. Should skills be Python-only or support multiple languages?  

---

## 8. Development Milestones

1. **Backend Scaffold**  
   - FastAPI server with MCP endpoints and health check.  
   - SkillEngine stub with hardcoded skills.  

2. **Skill Generation**  
   - OpenAI integration.  
   - Natural language → Python code.  
   - Register and execute new skills.  

3. **Frontend Scaffold**  
   - Chat panel connected to backend.  
   - Skill viewer and MCP spec viewer.  

4. **End-to-End Demo**  
   - User requests new skill.  
   - AutoLearn generates and crystalizes code.  
   - Frontend displays skill + MCP spec.  
   - Skill executes successfully.  

---