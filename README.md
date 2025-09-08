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
- **Frontend Demo**: Chat, code viewer, MCP schema viewer, and execution panel.  

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, OpenAI API  
- **Frontend**: React, Tailwind CSS  
- **Testing**: Pytest (backend), Jest/React Testing Library (frontend)  

---

## Repository Structure

autolearn/
├── backend/          # FastAPI MCP server + skill engine
│   └── tests/        # Unit and integration tests
├── frontend/         # React demo app
├── docs/             # Documentation (PRD, design notes)
└── README.md

---

## Getting Started

### 1. Clone the Repository
git clone https://github.com/<your-org>/autolearn.git
cd autolearn

### 2. Backend Setup
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

Run the backend:
uvicorn main:app --reload

### 3. Frontend Setup
cd frontend
npm install
npm run dev

Frontend runs on http://localhost:5173  
Backend runs on http://localhost:8000  

---

## Testing

### Backend
pytest

### Frontend
npm test

---

## Development Milestones

1. **Backend Scaffold** – FastAPI server + stubbed skills.  
2. **Skill Generation** – OpenAI-powered Python code generation.  
3. **Frontend Scaffold** – Chat + viewers connected to backend.  
4. **End-to-End Demo** – Dynamic skill creation, MCP updates, execution.  

---

## Documentation

Full details in `docs/PRD.md`.  

---

## License

[TBD]
