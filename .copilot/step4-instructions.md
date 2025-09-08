Title: Milestone 4 - User Mode MVP (1 Hour Implementation)

Summary:
- Create simple user mode where users can request new skills through chat
- Basic MCP client that connects to AutoLearn server and generates skills on demand
- Minimal frontend enhancement to show user skill requests working end-to-end
- Proof of concept that demonstrates the core auto-learning functionality

PRD Milestone 4 Requirements:
- User can manually request a new skill to be created
- AutoLearn generates and crystalizes code into persistent skill
- Frontend can display skill (including code) + updated MCP spec
- User can then prompt the frontend chat to use the new skill, which executes successfully
- This requires an AI consumer agent that uses MCP to connect to AutoLearn
- Consumer Agent configured to send recent reasoning to AutoLearn automatically (future)
- AutoLearn crystalizes code for recent runs and presents as new hardcoded skills (future)

What Copilot should produce (core features):
1. MCP Client Agent:
   - Intelligent consuming agent that connects to AutoLearn MCP server via JSON-RPC 2.0
   - Natural language processing to identify when new skills are needed
   - Automatic skill generation requests to AutoLearn server
   - Smart skill discovery and reuse for similar user requests
   - Conversation memory and context awareness for skill suggestions

2. Enhanced User Interface:
   - Improved chat interface focused on user skill requests rather than system demo
   - Skill request flow with clear user intent capture
   - Real-time skill generation progress indicator with status updates
   - Skill discovery panel showing existing skills that might satisfy user needs
   - User-friendly skill management (view, edit, delete skills)

3. Intelligent Skill Lifecycle:
   - Smart detection of when user requests require new skill creation
   - Automatic skill naming and categorization based on user intent
   - Skill deduplication to avoid creating redundant skills
   - Skill recommendation engine for similar requests

Style & constraints (must follow):
- MCP client must use proper JSON-RPC 2.0 protocol over HTTP transport
- Frontend must maintain T3 stack (Next.js, TypeScript, Tailwind CSS, tRPC) with shadcn/ui
- Agent must be implemented in Python with OpenAI integration for NLP and reasoning
- All user interactions must be intuitive and provide clear feedback
- Skill generation must be transparent with user visibility into the process
- Performance must be responsive with loading states and progress indicators
- Skip authentication/security for this proof of concept

APIs (surface contract):
- New MCP Client Agent endpoints:
  - POST /agent/chat: Send user message and get agent response with skill actions
  - GET /agent/skills/suggestions: Get skill suggestions based on user query
  - POST /agent/skills/request: Request new skill generation with user context
  - GET /agent/conversation/{id}: Get conversation history with skill creation context

- Enhanced Frontend API integration:
  - Real-time WebSocket events for skill generation progress
  - Skill search and filtering capabilities
  - Enhanced MCP tools discovery and execution

Frontend Components (detailed):
1. UserChatView:
   - Natural conversation interface with MCP client agent
   - Smart skill suggestion bubbles for relevant existing skills
   - Clear indication when agent is generating new skills
   - Context-aware responses with skill integration opportunities

2. SkillDiscoveryView:
   - Search interface for finding relevant existing skills
   - Skill categorization and tagging system
   - Usage statistics and popularity indicators
   - Preview and quick-test functionality for skills

3. SkillGenerationView:
   - Real-time progress tracking for skill generation
   - Generated skill preview with code and metadata
   - Testing interface for validating new skills
   - Registration confirmation and immediate availability

4. UserSkillsView:
   - Personal skill library with organization tools
   - Usage history and performance metrics
   - Batch operations (delete, categorize, export)

Acceptance criteria (tests to produce):
- MCP client agent successfully connects to AutoLearn server
- User can request new skills through natural language conversation
- Agent accurately identifies when new skill creation is needed vs using existing skills
- Skill generation process is transparent with real-time progress updates
- Generated skills appear in user's skill library and are immediately usable
- Skill discovery helps users find existing skills before creating duplicates
- Error states provide helpful guidance and recovery options
- Performance is responsive with appropriate loading states and feedback

Edge cases & notes for Copilot:
- Handle OpenAI API rate limits and timeouts gracefully
- Implement skill deduplication logic to avoid creating redundant skills
- Consider user context and conversation history for better skill suggestions
- Handle partial skill generation failures with user-friendly error messages
- Implement proper user session management and persistence
- Plan for skill versioning and update workflows
- Handle concurrent skill generation requests appropriately
- Skip authentication and advanced security for this proof of concept

NICE TO HAVE (for future milestones):
- User approval workflows before skill creation (auto-approve for now)
- Advanced security hardening and input validation
- Authentication and multi-user support
- Enterprise features (teams, organizations, billing)
- Mobile-responsive design and PWA capabilities
- Advanced analytics and telemetry
- Deployment packaging and infrastructure
- Multi-language skill support beyond Python

Developer guidance for running locally (implementation):
- MCP Client Agent: `python -m backend.mcp_client_agent --server-url http://localhost:8000/mcp`
- Backend: `uvicorn backend.app:app --reload` (AutoLearn MCP server)
- Frontend: Navigate to `frontend/` and run `npm run dev` with enhanced user mode UI
- Test agent integration: Use new `/agent/chat` endpoint for user conversations
- Validate skill generation: Monitor real-time WebSocket events for progress updates

Architecture decisions to implement:
- MCP client agent as separate Python module with OpenAI integration
- Enhanced frontend components with user-centric design patterns
- Intelligent skill deduplication and recommendation engine
- Conversation context persistence for improved user experience
- Performance optimization for real-time skill generation feedback
- Skip security/auth but keep all intelligent features

Notes and assumptions:
- User mode focuses on explicit skill requests with intelligent detection
- MCP client agent serves as intelligent intermediary between user and AutoLearn server
- Skill generation should be fast enough for real-time user interaction (< 30 seconds)
- Frontend should guide users toward existing skills before creating new ones
- Conversation history enables better context-aware skill suggestions
- Auto-approve generated skills for this proof of concept
