# AutoLearn

AutoLearn is a **Model Context Protocol (MCP) server** that lets AI agents dynamically create and reuse new **skills** (functional code workflows) from natural language.  

Unlike static MCP servers, AutoLearn introduces a **coding agent** that:  
- Converts reasoning traces into **crystalized memory** (Python functions).  
- Decides automatically which workflows to crystalize.  
- Updates its **MCP spec** dynamically so consuming agents can use new skills immediately.  

[![AutoLearn Demo](https://github.com/tarkaai/autolearn/blob/a900df9a18ff6675fc904e7f51f37b3e450726df/video-thumbnail.png)](https://www.youtube.com/watch?v=s_9m4P9_6jc)

Learn More: https://www.autolearn.dev/

The project includes a **frontend demo app** where users can:  
- Chat with a consuming agent that uses AutoLearn.  
- See auto-generated Python code for new skills.  
- View the updated MCP spec in real time.  
- Execute skills interactively.  

---

## Features

- **Dynamic Skill Creation**: Natural language → Python code workflows via OpenAI integration
- **Crystalized Memory**: Frequently used or complex reasoning preserved as executable code  
- **MCP Server**: Full JSON-RPC 2.0 protocol compliance over HTTP transport
- **Real-Time Updates**: WebSocket events for skill_added, skill_executed, mcp_updated
- **Persistence**: SQLite database for skills, sessions, and operational data
- **Frontend Demo**: T3 stack with chat, skill viewer, MCP spec viewer, and execution panel
- **Comprehensive Testing**: 54/54 tests passing with full integration coverage  

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, OpenAI API  
- **Frontend**: T3 Stack (Next.js, TypeScript, Tailwind CSS, tRPC) with shadcn/ui components  
- **Testing**: Pytest (backend), Vitest (frontend)  

---

## Repository Structure

```
autolearn/
├── backend/          # FastAPI MCP server + skill engine
│   ├── app.py        # FastAPI application
│   ├── schemas.py    # Pydantic models
│   ├── skill_engine.py # Skill registry and execution
│   └── openai_client.py # OpenAI integration
├── frontend/         # T3 Stack frontend (Next.js, TypeScript, Tailwind, tRPC)
│   ├── src/          # Source code
│   │   ├── components/   # UI components using shadcn/ui
│   │   ├── pages/    # Next.js pages
│   │   └── server/   # tRPC router definitions
├── tests/            # Unit and integration tests
├── docs/             # Documentation (PRD, design notes)
├── skills.db         # SQLite database for skill persistence
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- OpenAI API key

### 1. Clone the Repository
```bash
git clone https://github.com/tarkaai/autolearn.git
cd autolearn
```

### 2. Backend Setup
```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e .   # Install in development mode
```

### 3. Set up OpenAI API Key
```bash
# Option 1: Create a .env file (recommended)
cp .env.example .env
# Edit .env with your API key

# Option 2: Set environment variables directly
export OPENAI_API_KEY=your-api-key-here
export OPENAI_MODEL=gpt-4.1-mini  # Optional, default is gpt-4.1
```

### 4. Run the Server
```bash
# Using the convenience script (loads .env automatically)
python server.py

# Or directly with uvicorn
uvicorn backend.app:app --reload
```

The API will be available at http://localhost:8000

### 5. Frontend Setup
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at http://localhost:3000

---

## API Endpoints

### MCP Protocol (JSON-RPC 2.0)
- `POST /mcp` - MCP server endpoint for tools discovery and execution

### REST API  
- `GET /health` - Health check
- `GET /tools` - List all registered skills
- `GET /skills/{skill_id}` - Get specific skill details
- `POST /skills/generate` - Generate a new skill from natural language
- `POST /skills/register` - Register a generated skill
- `DELETE /skills/{skill_id}` - Delete a skill

### WebSocket
- `WS /ws` - Real-time events (skill_added, skill_executed, mcp_updated)

### Session Management
- `GET /sessions` - List chat sessions
- `POST /sessions` - Create new session
- `GET /sessions/{id}` - Get session details
- `POST /sessions/{id}/messages` - Add message to session

## Example: MCP Client Integration

AutoLearn implements the full MCP (Model Context Protocol) specification. Here's how to use it:

### 1. MCP Tools Discovery
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

### 2. Execute MCP Tool
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "tools/call",
    "params": {
      "name": "circle_area",
      "arguments": {"radius": 5}
    },
    "id": 2
  }'
```

### 3. Generate New Skill via REST API
```bash
curl -X POST http://localhost:8000/skills/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "Create a function that calculates the area of a circle", "name": "circle_area"}'
```

### 4. Frontend Demo
Visit http://localhost:3000 to see the full demo with:
- Chat interface showing MCP server capabilities  
- Real-time skill generation and registration
- Live MCP specification updates
- Interactive skill execution with parameter forms

---

## Testing

AutoLearn has comprehensive test coverage with 54/54 tests passing:

```bash
# Run all tests (54 total tests)
pytest

# Run with verbose output
pytest -v

# Run specific test categories
pytest tests/test_backend_basic.py    # Basic functionality (19 tests)
pytest tests/test_milestone2.py       # Skill generation (15 tests) 
pytest tests/test_milestone3*.py      # MCP integration (20 tests)

# Run tests with coverage
pytest --cov=backend --cov-report=html
```

Test categories:
- **Backend Core**: API endpoints, database operations, error handling
- **Skill Engine**: OpenAI integration, code generation, skill registration  
- **MCP Protocol**: JSON-RPC 2.0 compliance, tool discovery, execution
- **WebSocket**: Real-time events, connection handling
- **Integration**: End-to-end workflows, frontend-backend communication

---

## Development Status

### ✅ COMPLETED - Milestone 3: Full Stack MCP Server
- **MCP Protocol**: Complete JSON-RPC 2.0 implementation over HTTP transport
- **Frontend Integration**: T3 stack with WebSocket real-time updates  
- **Skill Management**: Full CRUD operations with persistent SQLite storage
- **Testing**: Comprehensive test suite with 54/54 tests passing (100% success rate)
- **Demo Application**: Multi-view interface showcasing all AutoLearn capabilities

### 🎯 NEXT PHASE - MCP Ecosystem Expansion  
- **stdio Transport**: Enable desktop MCP clients (Claude Desktop, etc.)
- **Meta-Capabilities**: Expose skill generation itself as an MCP tool
- **Enhanced Security**: Process isolation and resource limits for skill execution
- **Production Features**: Multi-client support, monitoring, deployment packaging  

---

## Environment Configuration

AutoLearn uses environment variables for configuration:

1. Create a `.env` file in the project root:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=sk-your-api-key-here
```

3. Optional settings:
```
# Choose a different OpenAI model
OPENAI_MODEL=gpt-4.1-mini

# Set logging level
LOG_LEVEL=DEBUG

# Customize database path (default is skills.db in project root)
DB_PATH=/path/to/custom/skills.db
```

The `server.py` script automatically loads variables from the `.env` file when starting the server.

---

## Documentation

Full details in `docs/PRD.md`.

## Security Considerations

**Current Implementation:**
- Skills execute with direct Python execution and comprehensive error handling
- Input validation on all API endpoints with Pydantic schema validation
- WebSocket connections properly managed with graceful disconnection handling
- SQLite database operations use parameterized queries to prevent injection

**Planned Security Enhancements:**
- Process isolation for skill execution with resource limits (CPU, memory, time)
- Enhanced sandboxing with restricted Python environment
- Rate limiting for skill generation and execution requests
- Audit logging for all skill operations and user interactions

**Development Guidelines:**
- All generated skills include proper error handling and input validation
- OpenAI API calls are rate-limited and include retry logic
- Database connections use connection pooling with proper cleanup

## Persistence

AutoLearn uses SQLite for persistent storage of skills:

- Skills are automatically saved to a database file (`skills.db` by default)
- All registered skills are restored when the server restarts
- Skills persist their metadata, source code, and other attributes
- You can customize the database path using the `DB_PATH` environment variable

This ensures that:
1. Skills you create are not lost when the server restarts
2. Your AI assistant can build on previously created skills
3. You can back up or version control your skills database

---

## License

[MIT License](LICENSE.md) 2025 Tarka Ventures, Inc.
