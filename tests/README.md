# AutoLearn Test Suite

This directory contains the organized test suite for the AutoLearn project. Tests are categorized by their purpose and scope.

## Directory Structure

```
tests/
├── __init__.py
├── unit/                   # Unit tests for individual components
│   ├── __init__.py
│   ├── backend_basic.py
│   ├── consumer_agent_basic.py
│   ├── fibonacci_fix.py
│   ├── function_calling.py
│   ├── harness.py
│   └── parameter_fix.py
├── integration/            # Integration tests for multiple components
│   ├── __init__.py
│   ├── frontend_chat_integration.py
│   ├── frontend_chat_spec.py
│   ├── milestone2.py
│   └── milestone3_chat.py
├── agent/                  # Tests for consumer agent functionality
│   ├── __init__.py
│   ├── ai_analysis.py
│   ├── autolearn_diagnosis.py
│   ├── automatic_improvement.py
│   ├── consumer_agent_skill_execution.py
│   ├── conversation_context.py
│   ├── full_agent.py
│   ├── skill_error_handling.py
│   ├── skill_prevention.py
│   └── skill_selection_debug.py
├── mcp/                    # MCP (Model Context Protocol) tests
│   ├── __init__.py
│   ├── mcp_compliance.py
│   ├── mcp_http.py
│   ├── mcp_integration.py
│   ├── mcp_proof.py
│   └── mcp_protocol.py
└── openai_integration/     # OpenAI integration tests
    ├── __init__.py
    └── openai.py
```

## Running Tests

### Using the Test Runner

The project includes a convenient test runner script:

```bash
# Run all tests
python run_tests.py

# Run specific categories
python run_tests.py unit
python run_tests.py integration
python run_tests.py agent
python run_tests.py mcp
python run_tests.py openai

# Run with verbose output
python run_tests.py unit -v
```

### Using pytest directly

```bash
# Run all tests
pytest tests/

# Run specific categories
pytest tests/unit/
pytest tests/integration/
pytest tests/agent/
pytest tests/mcp/
pytest tests/openai/

# Run with markers (if implemented)
pytest -m "unit"
pytest -m "not slow"

# Run specific test files
pytest tests/unit/backend_basic.py
pytest tests/agent/skill_error_handling.py

# Run with verbose output
pytest -v tests/
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **backend_basic.py**: Basic backend functionality tests
- **consumer_agent_basic.py**: Basic consumer agent tests
- **fibonacci_fix.py**: Tests for fibonacci calculation fixes
- **function_calling.py**: Function calling mechanism tests
- **harness.py**: Test harness functionality
- **parameter_fix.py**: Parameter handling and fixing tests

### Integration Tests (`tests/integration/`)
- **frontend_chat_integration.py**: Frontend-backend chat integration
- **frontend_chat_spec.py**: Chat specification tests
- **milestone2.py**: Milestone 2 integration tests
- **milestone3_chat.py**: Milestone 3 chat functionality tests

### Agent Tests (`tests/agent/`)
- **ai_analysis.py**: AI-driven skill analysis tests
- **autolearn_diagnosis.py**: Automatic learning diagnosis
- **automatic_improvement.py**: Automatic improvement functionality
- **consumer_agent_skill_execution.py**: Skill execution tests
- **conversation_context.py**: Conversation context management
- **full_agent.py**: Full agent functionality tests
- **skill_error_handling.py**: Error handling in skills
- **skill_prevention.py**: Skill prevention mechanisms
- **skill_selection_debug.py**: Skill selection debugging

### MCP Tests (`tests/mcp/`)
- **mcp_compliance.py**: MCP protocol compliance tests
- **mcp_http.py**: MCP over HTTP tests
- **mcp_integration.py**: MCP integration tests
- **mcp_proof.py**: MCP proof of concept tests
- **mcp_protocol.py**: Core MCP protocol tests

### OpenAI Tests (`tests/openai/`)
- **openai.py**: OpenAI API integration tests

## Configuration

The test suite uses pytest with configuration in `pytest.ini`. Key settings:

- Test discovery: Finds all `.py` files in the `tests/` directory
- Markers: Support for categorizing tests (unit, integration, agent, mcp, openai, slow)
- Output: Short traceback format with verbose output

## Environment Setup

Many tests require environment variables to be set:

```bash
# Required for OpenAI tests
export OPENAI_API_KEY="your-api-key-here"

# Load from .env file (recommended)
# Create a .env file in the project root with:
# OPENAI_API_KEY=your-api-key-here
```

## Adding New Tests

When adding new tests:

1. Place them in the appropriate category directory
2. Follow the naming convention (no `test_` prefix)
3. Add appropriate docstrings and comments
4. Consider adding markers for test categorization
5. Update this README if adding new categories

## Continuous Integration

The organized test structure supports different CI strategies:

```yaml
# Example GitHub Actions matrix
strategy:
  matrix:
    test-category: [unit, integration, agent, mcp, openai]
```

This allows running different test categories in parallel for faster CI builds.
