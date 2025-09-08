# AutoLearn

AutoLearn is a **Model Context Protocol (MCP) server** that lets AI agents dynamically create and reuse new **skills** (functional code workflows) from natural language.  

Unlike static MCP servers, AutoLearn introduces a **coding agent** that:  
- Converts reasoning traces into **crystalized memory** (Python functions).  
- Decides automatically which workflows to crystalize.  
- Updates its **MCP spec** dynamically so consuming agents can use new skills immediately.  

The project includes a **frontend demo app** where users can:  
- Chat with a consuming agent that uses AutoLearn.  
- See auto-generated Python code for new skills.  
- View the updated MCP spec in real time.  
- Execute skills interactively.  

---

## Features

- **Dynamic Skill Creation**: Natural language → Python code workflows.  
- **Crystalized Memory**: Frequently used or complex reasoning preserved as code.  
- **MCP Integration**: Skills instantly exposed to consuming agents.  
- **Persistence**: SQLite database for storing skills between server restarts.
- **Frontend Demo**: Chat, code viewer, MCP schema viewer, and execution panel.  

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, OpenAI API  
- **Frontend**: React, Tailwind CSS  
- **Testing**: Pytest (backend), Jest/React Testing Library (frontend)  

---

## Repository Structure

```
autolearn/
├── backend/          # FastAPI MCP server + skill engine
│   ├── app.py        # FastAPI application
│   ├── schemas.py    # Pydantic models
│   ├── skill_engine.py # Skill registry and execution
│   └── openai_client.py # OpenAI integration
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
git clone https://github.com/<your-org>/autolearn.git
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

---

## API Endpoints

- `GET /health` - Health check
- `GET /tools` - List all registered skills
- `GET /mcp` - Get MCP specification
- `POST /run` - Execute a skill
- `POST /skills/generate` - Generate a new skill from natural language
- `POST /skills/register` - Register a generated skill

## Example: Creating a New Skill

1. Generate skill code:

```bash
curl -X POST http://localhost:8000/skills/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "Create a function that calculates the area of a circle", "name": "circle_area"}'
```

2. Register the generated skill:

```bash
curl -X POST http://localhost:8000/skills/register \
  -H "Content-Type: application/json" \
  -d '{"code": "...", "meta": {...}}'
```

3. Use the skill:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"name": "circle_area", "args": {"radius": 5}}'
```

---

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_milestone2.py
```

---

## Development Milestones

1. ✅ **Backend Scaffold** – FastAPI server + stubbed skills.  
2. ✅ **Skill Generation** – OpenAI-powered Python code generation.  
3. 📝 **Frontend Scaffold** – Chat + viewers connected to backend.  
4. 📝 **End-to-End Demo** – Dynamic skill creation, MCP updates, execution.  

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

The current implementation executes generated code in the same process as the server. Future versions will add sandboxing for safer code execution.

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

[TBD]
